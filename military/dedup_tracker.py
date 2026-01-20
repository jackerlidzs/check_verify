"""
Deduplication Tracker for Military Verification
Tracks used veteran data to prevent re-verification
"""
import json
from pathlib import Path
from typing import Set
import hashlib


class DeduplicationTracker:
    """Track used veteran data to prevent duplicate verifications."""
    
    def __init__(self, filepath: str = "military/data/used_veterans.txt"):
        self.filepath = Path(filepath)
        self.used_set: Set[str] = set()
        self._load()
    
    def _load(self):
        """Load used records from file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.used_set.add(line)
            except Exception as e:
                print(f"[WARN] Could not load used file: {e}")
    
    def _save(self):
        """Save used records to file."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write("# Used veteran records (FIRSTNAME|LASTNAME|DOB)\n")
            f.write("# One per line, do not edit manually\n\n")
            for key in sorted(self.used_set):
                f.write(f"{key}\n")
    
    def _make_key(self, firstname: str, lastname: str, dob: str) -> str:
        """Create unique key from veteran info."""
        # Normalize
        fn = firstname.strip().upper()
        ln = lastname.strip().upper()
        birth = dob.strip().replace('/', '-')
        
        return f"{fn}|{ln}|{birth}"
    
    def is_used(self, firstname: str, lastname: str, dob: str) -> bool:
        """Check if veteran data has been used."""
        key = self._make_key(firstname, lastname, dob)
        return key in self.used_set
    
    def mark_used(self, firstname: str, lastname: str, dob: str):
        """Mark veteran data as used."""
        key = self._make_key(firstname, lastname, dob)
        self.used_set.add(key)
        self._save()
    
    def get_count(self) -> int:
        """Get count of used records."""
        return len(self.used_set)
    
    def clear(self):
        """Clear all used records."""
        self.used_set.clear()
        if self.filepath.exists():
            self.filepath.unlink()


def filter_unused_veterans(veterans: list, tracker: DeduplicationTracker) -> list:
    """Filter out veterans that have already been used."""
    unused = []
    skipped = 0
    
    for v in veterans:
        fn = v.get('firstname', '')
        ln = v.get('lastname', '')
        dob = v.get('birth', '')
        
        if not fn or not ln or not dob:
            continue
        
        if tracker.is_used(fn, ln, dob):
            skipped += 1
            continue
        
        unused.append(v)
    
    if skipped > 0:
        print(f"[DEDUP] Skipped {skipped} already used veterans")
    
    return unused


if __name__ == "__main__":
    # Test
    tracker = DeduplicationTracker()
    
    print(f"Currently used: {tracker.get_count()}")
    
    # Test mark and check
    tracker.mark_used("JOHN", "SMITH", "1990-05-15")
    print(f"After marking 1: {tracker.get_count()}")
    
    print(f"Is JOHN SMITH used? {tracker.is_used('JOHN', 'SMITH', '1990-05-15')}")
    print(f"Is JANE DOE used? {tracker.is_used('JANE', 'DOE', '1985-03-20')}")
