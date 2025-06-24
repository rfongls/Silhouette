# TEST_SCENARIOS.md

This document defines input/output scenarios for major Silhouette Core components.

## 🎯 Intent Engine

### Scenario 1: Known phrase
Input: `"Reload everything"`  
Expected Output: `{ "intent": "reload_config", "confidence": 0.9 }`

### Scenario 2: Unknown phrase
Input: `"Tell me something cool"`  
Expected Output: `{ "intent": "unknown", "confidence": 0.2 }`

## 🧠 Memory Core

### Scenario 1: Append and search
1. Append: `{ "text": "User asked about memory." }`
2. Search: `"memory"`  
Expected Output: Entry is returned with timestamp

## 😐 Tone Parser

### Scenario 1: Happy text
Input: `"I am so excited for this launch!"`  
Expected Output: `{ "tone": "happy", "confidence": 0.9 }`

### Scenario 2: Confused text
Input: `"I don’t get what’s going on"`  
Expected Output: `{ "tone": "confused", "confidence": 0.9 }`

## 🌐 API Interface

### Scenario: Memory endpoint usage
POST `/memory` with `{ "text": "Persistent entry test" }`  
Then GET `/memory?q=test`  
Expected: Returns previously submitted entry
