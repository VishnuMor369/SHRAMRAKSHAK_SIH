"""
SHRAMRAKSHAK: Real E5-small-v2 Transformer & FAISS Semantic Memory Engine
SIH 2026 Problem Statement: SIH26165

Implements P1.3:
- Loads real transformer model: intfloat/e5-small-v2
- Correct E5 passage and query prefixes: "passage: " and "query: "
- Mean pooling with attention mask and L2 unit-norm normalization
- FAISS IndexFlatIP (Inner Product over normalized vectors = Cosine Similarity)
- ID mapping between FAISS integer IDs and Canonical SafetyEvent event_ids
- Incremental insertion, persistence to disk, and reload on startup
- Complete elimination of fake/random embeddings or TF-IDF heuristics
"""

import os
import json
import logging
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
import faiss
from typing import List, Dict, Tuple, Optional, Any

try:
    from backend.models_canonical import SafetyEvent
    from backend.database import db
except ImportError:
    try:
        from models_canonical import SafetyEvent
        from database import db
    except ImportError:
        from ..models_canonical import SafetyEvent
        from ..database import db

logger = logging.getLogger("SemanticMemory")

MODEL_NAME = "intfloat/e5-small-v2"
EMBEDDING_DIM = 384
INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
INDEX_PATH = os.path.join(INDEX_DIR, "e5_faiss.index")
MAP_PATH = os.path.join(INDEX_DIR, "e5_faiss_mapping.json")


class SemanticMemory:
    def __init__(self, model_name: str = MODEL_NAME, index_path: str = INDEX_PATH, map_path: str = MAP_PATH, db: Optional[Any] = None):
        self.model_name = model_name
        self.index_path = index_path
        self.map_path = map_path
        self.dim = EMBEDDING_DIM
        self.custom_db = db
        self.tokenizer = None
        self.model = None
        self.index = None
        self.id_to_event: Dict[int, str] = {}
        self.event_to_id: Dict[str, int] = {}
        self.next_id = 0
        
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self._init_model()
        self._init_index()

    def _get_db(self):
        """Returns injected database manager or module-level default."""
        return self.custom_db if self.custom_db is not None else db

    def _init_model(self):
        """Loads the official intfloat/e5-small-v2 transformer model."""
        logger.info(f"Loading transformer model {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()
        logger.info(f"Model {self.model_name} loaded into evaluation mode.")

    def _init_index(self):
        """Loads FAISS index from disk or creates a new IndexFlatIP."""
        if os.path.exists(self.index_path) and os.path.exists(self.map_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.map_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                    self.id_to_event = {int(k): v for k, v in mapping.get("id_to_event", {}).items()}
                    self.event_to_id = mapping.get("event_to_id", {})
                    self.next_id = mapping.get("next_id", 0)
                logger.info(f"Loaded existing FAISS index from {self.index_path} with {self.index.ntotal} vectors.")
                return
            except Exception as e:
                logger.warning(f"Failed to load FAISS index from {self.index_path}: {e}. Reinitializing.")

        self.index = faiss.IndexFlatIP(self.dim)
        self.id_to_event = {}
        self.event_to_id = {}
        self.next_id = 0
        logger.info(f"Created fresh FAISS IndexFlatIP(dim={self.dim}).")

    def _mean_pooling(self, model_output, attention_mask):
        """Standard mean pooling with attention mask for transformer sentence embeddings."""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def embed_texts(self, texts: List[str], prefix: str = "passage: ") -> np.ndarray:
        """
        Generates real normalized E5 embeddings.
        E5 requires 'passage: ' prefix for corpus documents and 'query: ' for queries.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        prefixed_texts = [f"{prefix}{t.strip()}" for t in texts]
        encoded_input = self.tokenizer(
            prefixed_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            model_output = self.model(**encoded_input)
            sentence_embeddings = self._mean_pooling(model_output, encoded_input["attention_mask"])
            # L2 normalize embeddings so inner product equals cosine similarity
            sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)

        return sentence_embeddings.cpu().numpy().astype(np.float32)

    def build_event_passage(self, event: SafetyEvent) -> str:
        """Constructs a high-signal structured representation of a safety event for embedding."""
        parts = []
        if event.activity:
            parts.append(f"activity: {event.activity}")
        if event.energy:
            parts.append(f"hazard energy: {event.energy}")
        if event.exposure:
            parts.append(f"exposure: {event.exposure}")
        if event.barrier:
            b_str = ", ".join(event.barrier)
            s_str = ", ".join(event.barrier_state)
            parts.append(f"barriers: {b_str} ({s_str})")
        if event.consequence:
            parts.append(f"consequence: {event.consequence}")
        if event.narrative:
            clean_narrative = " ".join(event.narrative.split())[:300]
            parts.append(f"narrative: {clean_narrative}")
        return " | ".join(parts)

    def add_event(self, event: SafetyEvent) -> str:
        """Embeds and indexes a single Canonical SafetyEvent into FAISS and persists."""
        if event.event_id in self.event_to_id:
            # Event already indexed
            return event.event_id

        passage = self.build_event_passage(event)
        vec = self.embed_texts([passage], prefix="passage: ")
        
        idx = self.next_id
        self.index.add(vec)
        self.id_to_event[idx] = event.event_id
        self.event_to_id[event.event_id] = idx
        self.next_id += 1

        # Link embedding ID to event
        event.embedding_id = f"emb-{event.event_id}"

        # Persist FAISS index and mapping
        self.save_index()

        # Ensure event is persisted in events table first to satisfy foreign key
        active_db = self._get_db()
        try:
            if not active_db.get_event(event.event_id):
                active_db.save_event(event)
        except Exception:
            pass

        # Log into SQLite embeddings table
        with active_db.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO embeddings (embedding_id, event_id, model_name, dim, passage_text, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (event.embedding_id, event.event_id, self.model_name, self.dim, passage))

        return event.event_id

    # Alias for indexing
    index_event = add_event

    def add_events_batch(self, events: List[SafetyEvent], batch_size: int = 32) -> int:
        """Batch embedding and FAISS indexing for fast, efficient dataset ingestion with SQLite synchronization (Rule 13)."""
        new_events = [e for e in events if e.event_id not in self.event_to_id]
        if not new_events:
            return 0

        total_added = 0
        embeddings_to_insert = []
        for i in range(0, len(new_events), batch_size):
            batch = new_events[i:i + batch_size]
            passages = [self.build_event_passage(e) for e in batch]
            vecs = self.embed_texts(passages, prefix="passage: ")
            
            for j, e in enumerate(batch):
                idx = self.next_id
                self.index.add(vecs[j:j+1])
                self.id_to_event[idx] = e.event_id
                self.event_to_id[e.event_id] = idx
                self.next_id += 1
                e.embedding_id = f"emb-{e.event_id}"
                total_added += 1
                embeddings_to_insert.append((
                    e.embedding_id, e.event_id, self.model_name, self.dim, passages[j]
                ))

        self.save_index()

        # Synchronize batch embeddings into SQLite
        active_db = self._get_db()
        if embeddings_to_insert:
            try:
                with active_db.get_connection() as conn:
                    conn.executemany("""
                    INSERT OR REPLACE INTO embeddings (embedding_id, event_id, model_name, dim, passage_text, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, embeddings_to_insert)
            except Exception as ex:
                logger.warning(f"Error persisting batch embeddings to SQLite: {ex}")

        return total_added

    def search_candidates(self, query_text: str, top_k: int = 10, min_similarity: float = 0.50) -> List[Tuple[str, float]]:
        """
        Stage 1 Retrieval: Searches for nearest safety events using cosine similarity.
        Returns [(event_id, similarity_score), ...].
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vec = self.embed_texts([query_text], prefix="query: ")
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vec, k)

        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx in self.id_to_event and dist >= min_similarity:
                candidates.append((self.id_to_event[idx], float(dist)))

        return candidates

    def search_similar_events(self, target_event: SafetyEvent, top_k: int = 10, min_similarity: float = 0.50) -> List[Tuple[str, float]]:
        """Searches candidates using structured event attributes and narrative context."""
        query_parts = [
            target_event.activity or "",
            target_event.energy or "",
            target_event.exposure or "",
            " ".join(target_event.barrier or []),
            target_event.consequence or ""
        ]
        if target_event.narrative:
            query_parts.append(" ".join(target_event.narrative.split())[:200])
        query_text = " ".join([p for p in query_parts if p.strip()])

        candidates = self.search_candidates(query_text, top_k=top_k + 1, min_similarity=min_similarity)
        # Exclude self
        return [(eid, sim) for eid, sim in candidates if eid != target_event.event_id][:top_k]

    def check_index_integrity(self) -> Dict[str, Any]:
        """
        Verifies FAISS index vs SQLite database integrity (Rule 13).
        Identifies orphan mappings, unindexed events, and missing SQLite embeddings.
        """
        active_db = self._get_db()
        with active_db.get_connection() as conn:
            sqlite_events = set(r[0] for r in conn.execute("SELECT event_id FROM events").fetchall())
            sqlite_embeddings = set(r[0] for r in conn.execute("SELECT event_id FROM embeddings").fetchall())
        
        faiss_events = set(self.id_to_event.values())
        orphan_faiss_events = [eid for eid in faiss_events if eid not in sqlite_events]
        unindexed_events = [eid for eid in sqlite_events if eid not in faiss_events]
        missing_sqlite_embeddings = [eid for eid in faiss_events if eid not in sqlite_embeddings and eid in sqlite_events]

        return {
            "faiss_total_vectors": self.index.ntotal if self.index else 0,
            "faiss_mapped_events": len(self.id_to_event),
            "sqlite_total_events": len(sqlite_events),
            "sqlite_embeddings_count": len(sqlite_embeddings),
            "orphan_faiss_mappings_count": len(orphan_faiss_events),
            "unindexed_sqlite_events_count": len(unindexed_events),
            "missing_sqlite_embeddings_count": len(missing_sqlite_embeddings),
            "is_synchronized": (len(orphan_faiss_events) == 0 and len(unindexed_events) == 0 and len(missing_sqlite_embeddings) == 0)
        }

    def reconcile_and_rebuild(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes atomic reconciliation & rebuild of FAISS index, mappings, and SQLite embeddings (Phase 8).
        Ensures 100% bijective invariant:
        Active SQLite Events == SQLite Embeddings == FAISS Vectors == Mapping Entries.
        Zero orphan mappings, zero unindexed events, zero missing embeddings.
        """
        active_db = self._get_db()
        with active_db.get_connection() as conn:
            cur = conn.execute("SELECT event_id, activity, energy, exposure, barrier, barrier_state, consequence, narrative FROM events ORDER BY timestamp ASC, event_id ASC")
            raw_events = cur.fetchall()

        events_map = {}
        for row in raw_events:
            eid = row[0]
            b_list = json.loads(row[4]) if (row[4] and row[4].startswith("[")) else ([row[4]] if row[4] else [])
            b_state = json.loads(row[5]) if (row[5] and row[5].startswith("[")) else ([row[5]] if row[5] else [])
            events_map[eid] = SafetyEvent(
                event_id=eid,
                activity=row[1] or "",
                energy=row[2] or "",
                exposure=row[3] or "",
                barrier=b_list,
                barrier_state=b_state,
                consequence=row[6] or "",
                narrative=row[7] or ""
            )

        events_list = list(events_map.values())
        total_events = len(events_list)

        # Build clean temporary index and mapping
        tmp_index = faiss.IndexFlatIP(self.dim)
        tmp_id_to_event = {}
        tmp_event_to_id = {}
        embeddings_records = []

        batch_size = 32
        for i in range(0, total_events, batch_size):
            batch = events_list[i:i + batch_size]
            passages = [self.build_event_passage(e) for e in batch]
            vecs = self.embed_texts(passages, prefix="passage: ")
            
            for j, e in enumerate(batch):
                vid = i + j
                tmp_index.add(vecs[j:j+1])
                tmp_id_to_event[vid] = e.event_id
                tmp_event_to_id[e.event_id] = vid
                emb_id = f"emb-{e.event_id}"
                embeddings_records.append((
                    emb_id, e.event_id, self.model_name, self.dim, passages[j]
                ))

        # Validate temporary counts
        if tmp_index.ntotal != total_events or len(tmp_id_to_event) != total_events:
            raise RuntimeError(f"Rebuild validation failed: generated {tmp_index.ntotal} vectors for {total_events} events")

        # Write temporary files and atomically replace
        tmp_index_path = f"{self.index_path}.tmp"
        tmp_map_path = f"{self.map_path}.tmp"

        faiss.write_index(tmp_index, tmp_index_path)
        with open(tmp_map_path, "w", encoding="utf-8") as f:
            json.dump({
                "model_name": self.model_name,
                "dim": self.dim,
                "next_id": total_events,
                "id_to_event": tmp_id_to_event,
                "event_to_id": tmp_event_to_id
            }, f, indent=2)

        # Atomic replacement
        if os.path.exists(self.index_path):
            os.replace(tmp_index_path, self.index_path)
        else:
            os.rename(tmp_index_path, self.index_path)

        if os.path.exists(self.map_path):
            os.replace(tmp_map_path, self.map_path)
        else:
            os.rename(tmp_map_path, self.map_path)

        # Synchronize SQLite embeddings table
        with active_db.get_connection() as conn:
            conn.execute("DELETE FROM embeddings")
            conn.executemany("""
                INSERT INTO embeddings (embedding_id, event_id, model_name, dim, passage_text, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, embeddings_records)

        # Update live memory state
        self.index = tmp_index
        self.id_to_event = tmp_id_to_event
        self.event_to_id = tmp_event_to_id
        self.next_id = total_events

        logger.info(f"Reconciled and rebuilt semantic memory: {total_events} events, {tmp_index.ntotal} vectors, {len(embeddings_records)} embeddings.")

        return {
            "status": "PASS",
            "persistence_state": "COMMITTED",
            "events_count": total_events,
            "faiss_vectors": tmp_index.ntotal,
            "embeddings_count": len(embeddings_records),
            "orphan_mappings_count": 0,
            "unindexed_events_count": 0,
            "missing_embeddings_count": 0
        }

    def save_index(self):
        """Persists FAISS index binary and ID mapping to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, "w", encoding="utf-8") as f:
            json.dump({
                "model_name": self.model_name,
                "dim": self.dim,
                "next_id": self.next_id,
                "id_to_event": self.id_to_event,
                "event_to_id": self.event_to_id
            }, f, indent=2)

    def reload(self):
        """Reloads FAISS index and mappings from disk (used for restart verification)."""
        self._init_index()


# Global SemanticMemory instance
semantic_memory = SemanticMemory()
