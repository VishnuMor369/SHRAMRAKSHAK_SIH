"""
SHRAMRAKSHAK: Real NLP Preprocessor & Clause Segmentation
SIH 2026 Problem Statement: SIH26165

Implements P0.2:
- Preserves original raw text without alteration
- Preserves character offsets for every clause, token, and evidence span
- Sentence and clause/event segmentation (semicolons, coordinating conjunctions, subordinating temporal clauses)
- Tokenization with character offsets
- Extraction of temporal cues, modal expressions, conditional cues, negation cues, and uncertainty cues
- Never destroys original evidence; supports exact substring verification.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from .ontology import ontology


@dataclass
class TokenSpan:
    text: str
    start_offset: int
    end_offset: int


@dataclass
class ClauseSegment:
    segment_id: int
    text: str
    start_offset: int
    end_offset: int
    tokens: List[TokenSpan] = field(default_factory=list)
    temporal_cues: List[Dict[str, Any]] = field(default_factory=list)
    modal_cues: List[Dict[str, Any]] = field(default_factory=list)
    conditional_cues: List[Dict[str, Any]] = field(default_factory=list)
    negation_cues: List[Dict[str, Any]] = field(default_factory=list)
    uncertainty_cues: List[Dict[str, Any]] = field(default_factory=list)


class NLPPreprocessor:
    def __init__(self):
        self.clause_delimiters = re.compile(r'(;|(?<=\.)\s+|(?<=!)\s+|(?<=\?)\s+|\bwhile\b|\bbut\b|\bhowever\b|\balso\b|\bwhereas\b|\band\s+the\s+real\s+issue\b)', re.IGNORECASE)

    def tokenize_with_offsets(self, text: str, base_offset: int = 0) -> List[TokenSpan]:
        """Tokenize preserving exact character positions within the original raw text."""
        tokens = []
        for m in re.finditer(r'\b[A-Za-z0-9_-]+\b', text):
            tokens.append(TokenSpan(
                text=m.group(0),
                start_offset=base_offset + m.start(),
                end_offset=base_offset + m.end()
            ))
        return tokens

    def find_span_offsets(self, raw_text: str, search_pattern: str, base_start: int = 0, base_end: Optional[int] = None) -> List[Tuple[int, int, str]]:
        """Finds all non-overlapping occurrences of a regex or string with exact offsets."""
        results = []
        search_region = raw_text[base_start:base_end] if base_end is not None else raw_text[base_start:]
        for m in re.finditer(re.escape(search_pattern) if not search_pattern.startswith(r'\b') else search_pattern, search_region, re.IGNORECASE):
            abs_start = base_start + m.start()
            abs_end = base_start + m.end()
            results.append((abs_start, abs_end, raw_text[abs_start:abs_end]))
        return results

    def segment(self, raw_text: str) -> List[ClauseSegment]:
        """
        Segments raw_text into syntactic/semantic clauses while strictly preserving
        character offsets relative to raw_text.
        """
        if not raw_text:
            return []

        # Split on sentence boundaries, semicolons, and key clause boundaries
        split_matches = list(self.clause_delimiters.finditer(raw_text))
        segments = []
        current_start = 0

        for match in split_matches:
            split_start = match.start()
            split_end = match.end()
            clause_text = raw_text[current_start:split_start].strip()
            if clause_text:
                # Find exact start and end of stripped clause text
                lead_spaces = len(raw_text[current_start:split_start]) - len(raw_text[current_start:split_start].lstrip())
                actual_start = current_start + lead_spaces
                actual_end = actual_start + len(clause_text)
                
                seg = self._build_segment(raw_text, len(segments), actual_start, actual_end)
                segments.append(seg)
            
            # If the delimiter was a conjunction like 'while' or 'but', keep it in the next clause
            delim_str = match.group(0).strip().lower()
            if delim_str in ["while", "but", "however", "whereas"]:
                current_start = split_start
            else:
                current_start = split_end

        # Trailing clause
        if current_start < len(raw_text):
            clause_text = raw_text[current_start:].strip()
            if clause_text:
                lead_spaces = len(raw_text[current_start:]) - len(raw_text[current_start:].lstrip())
                actual_start = current_start + lead_spaces
                actual_end = actual_start + len(clause_text)
                seg = self._build_segment(raw_text, len(segments), actual_start, actual_end)
                segments.append(seg)

        # Fallback if no clauses split
        if not segments:
            lead_spaces = len(raw_text) - len(raw_text.lstrip())
            actual_start = lead_spaces
            actual_end = actual_start + len(raw_text.strip())
            segments.append(self._build_segment(raw_text, 0, actual_start, actual_end))

        return segments

    def _build_segment(self, raw_text: str, seg_id: int, start: int, end: int) -> ClauseSegment:
        text = raw_text[start:end]
        tokens = self.tokenize_with_offsets(text, base_offset=start)
        seg = ClauseSegment(
            segment_id=seg_id,
            text=text,
            start_offset=start,
            end_offset=end,
            tokens=tokens
        )
        
        # Analyze cues in this segment
        seg.temporal_cues = self._extract_cues(raw_text, start, end, ontology.uncertainty_rules.get("temporal_cues", {}))
        seg.modal_cues = self._extract_list_cues(raw_text, start, end, ontology.uncertainty_rules.get("modal_expressions", []))
        seg.conditional_cues = self._extract_list_cues(raw_text, start, end, ontology.uncertainty_rules.get("conditional_constructions", []))
        seg.negation_cues = self._extract_list_cues(raw_text, start, end, ontology.uncertainty_rules.get("negation_cues", []))
        seg.uncertainty_cues = self._extract_list_cues(raw_text, start, end, ontology.uncertainty_rules.get("double_negation_ambiguity", []))
        
        return seg

    def _extract_list_cues(self, raw_text: str, start: int, end: int, cue_list: List[str]) -> List[Dict[str, Any]]:
        cues = []
        clause_str = raw_text[start:end].lower()
        for cue in cue_list:
            pattern = r'\b' + re.escape(cue.lower()) + r'\b'
            for m in re.finditer(pattern, clause_str):
                c_start = start + m.start()
                c_end = start + m.end()
                cues.append({
                    "cue": cue,
                    "matched_text": raw_text[c_start:c_end],
                    "start_offset": c_start,
                    "end_offset": c_end
                })
        return cues

    def _extract_cues(self, raw_text: str, start: int, end: int, cue_dict: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        cues = []
        clause_str = raw_text[start:end].lower()
        for category, cue_list in cue_dict.items():
            for cue in cue_list:
                pattern = r'\b' + re.escape(cue.lower()) + r'\b'
                for m in re.finditer(pattern, clause_str):
                    c_start = start + m.start()
                    c_end = start + m.end()
                    cues.append({
                        "category": category,
                        "cue": cue,
                        "matched_text": raw_text[c_start:c_end],
                        "start_offset": c_start,
                        "end_offset": c_end
                    })
        return cues


preprocessor = NLPPreprocessor()
