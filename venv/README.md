# API Autocomplete Name Extractor

## Overview

This project systematically extracts all possible names from three versions of an autocomplete API:
- **v1**: Letter-only queries (`a-z`)
- **v2**: Letter and number queries (`a-z0-9`)
- **v3**: Letter and special character queries (`a-z+-. `)

Each version has its own dedicated Python script that generates and executes queries while respecting observed rate limits.

## Files

### Extraction Scripts
1. `v1_name_extractor.py` - Handles letter-only queries
2. `v2_name_extractor.py` - Handles letter and number queries
3. `v3_name_extractor.py` - Handles letter and special character queries

### Output Files
- `v1_names.json` - Results from v1 API
- `v2_names.json` - Results from v2 API
- `v3_names.json` - Results from v3 API

## API Observations

### Rate Limits (Observed via Postman)
| API Version | Rate Limit | Delay Between Requests |
|-------------|------------|------------------------|
| v1          | Not tested | 1.0s (conservative)    |
| v2          | 50/min     | 1.2s (60/50)           |
| v3          | 80/min     | 0.75s (60/80)          |

### Response Patterns
- **v1**: Returns max 10 results per query
- **v2**: Returns max 12 results per query
- **v3**: Returns max 15 results per query

## Implementation Approach

### Query Strategy
For each API version:
1. **1-character queries**: All possible single characters
2. **2-character queries**: All possible 2-character combinations

### Rate Limit Handling
- Each script maintains its own request counter
- Enforces minimum delay between requests
- Implements exponential backoff when rate-limited (429 responses)

### Progress Tracking
- Periodic saving of results to JSON files
- Ability to resume interrupted extractions
- Real-time progress logging with timestamps

## Performance Metrics

### Query Counts
| Version | Character Set | 1-Char | 2-Char | Total Queries |
|---------|--------------|--------|--------|---------------|
| v1      | a-z          | 26     | 676    | 702           |
| v2      | a-z0-9       | 36     | 1,296  | 1,332         |
| v3      | a-z+-.       | 29     | 841    | 870           |

### Estimated Runtime
| Version | Queries | Delay | Base Time | Estimated Total |
|---------|---------|-------|-----------|-----------------|
| v1      | 702     | 1.0s  | ~12 min   | ~15 min         |
| v2      | 1,332   | 1.2s  | ~27 min   | ~35 min         |
| v3      | 870     | 0.75s | ~11 min   | ~15 min         |

Note: Actual times may vary due to rate limiting and network conditions.

## Future Improvements

### What More Can Be Done
1. **v1**: Stop at 2-character queries when results < 10
2. **v2**: Stop at next level when results < 12
3. **v3**: Stop at next level when results < 15

### Additional Features
1. **3-character queries** for versions where max results are returned
2. **Dynamic query pruning** to skip unnecessary combinations
3. **Parallel processing** with careful rate limit coordination
4. **Better error recovery** for network issues
5. **Visual progress tracking** with progress bars


## Usage Instructions

1. Run each script in separate terminals:
   ```bash
   python v1_name_extractor.py
   python v2_name_extractor.py
   python v3_name_extractor.py
   ```

2. Results will be saved to respective JSON files.

3. Scripts can be safely interrupted and resumed.

4. Monitor progress in terminal output and log files.

## Additional Considerations
- **Error Handling**: Scripts include retry logic and exponential backoff for handling API failures.
- **Logging**: All scripts log their progress, errors, and key findings to ensure easy debugging.
- **Scalability**: The project structure allows easy expansion to other API versions or additional character sets.

## License
This project is for educational purposes only. Use at your own discretion.

---


