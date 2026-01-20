# Real Veterans Data - Manual Input

## Required Format

Add veterans data in the format below (one per line):
```
firstName|lastName|branch|birthDate|dischargeDate
```

## Field Details

| Field | Format | Example |
|-------|--------|---------|
| firstName | First name | JOHN |
| lastName | Last name | SMITH |
| branch | Military branch | ARMY, NAVY, AIR FORCE, MARINE CORPS, COAST GUARD |
| birthDate | YYYY-MM-DD | 1990-05-15 |
| dischargeDate | YYYY-MM-DD | 2025-01-15 (must be within 12 months) |

## Supported Branches

- ARMY (or US ARMY)
- NAVY (or US NAVY)
- AIR FORCE (or US AIR FORCE)
- MARINE CORPS (or US MARINE CORPS, MARINES)
- COAST GUARD (or US COAST GUARD)

## Example Data

```txt
JOHN|SMITH|ARMY|1990-05-15|2025-01-15
JANE|DOE|NAVY|1988-12-20|2025-03-01
MICHAEL|JOHNSON|AIR FORCE|1995-08-10|2025-06-15
DAVID|WILLIAMS|MARINE CORPS|1992-03-25|2025-02-28
```

## Important Notes

1. **Discharge Date MUST be within 12 months** (after Dec 29, 2024)
2. Names should be in UPPERCASE
3. Data must be from real veterans who consent to share
4. Each line = one veteran

## How to Use

1. Add your data to `military/data/real_veterans.txt`
2. Run: `python -m military.import_veterans`
3. Data will be converted to JSON and ready for verification
