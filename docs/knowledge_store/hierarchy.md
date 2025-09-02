# HL7 Hierarchy Reference

## Delimiters
- Field separator: `|`
- Component separator: `^`
- Subcomponent separator: `&`

## Example
```
PID|1||123456^^^Hospital^MR||Doe^John^A||19800101|M|||
```

## Explanation
- Field: `|` separates HL7 fields (e.g., PID fields)
- Component: `^` separates elements within a field (e.g., name parts)
- Subcomponent: `&` separates sub-elements inside a component
