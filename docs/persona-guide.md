# PERSONA_GUIDE.md

Silhouette Core can simulate tone, alignment, and behavioral traits through configuration and controlled response shaping.

---

## 🧠 Persona Injection via DSL

Define traits such as:

- Communication style (direct, empathetic, formal)
- Behavioral limits (refuse tasks, clarify ambiguity)
- Tone modifiers (sarcastic, friendly, stoic)

Example DSL (hypothetical):
```json
{
  "tone": "friendly",
  "alignment": "helpful",
  "deny_on": ["malicious", "deceptive", "violent"]
}
```

---

## 🎭 Tone Variants

Silhouette can be configured to emulate tone styles by injecting tone analysis into module responses:

| Tone       | Behavior Description            |
|------------|----------------------------------|
| Friendly   | Warm, affirming, and encouraging |
| Formal     | Professional and precise         |
| Curious    | Asks questions, explores deeper  |
| Skeptical  | Challenges assumptions           |

---

## 📚 Use Cases

- Developer assistant (analytical + direct)
- Mental health bot (empathetic + friendly)
- Compliance agent (formal + restrictive)

---

## ⚠️ Ethical Boundaries

Define hard-coded refusals via alignment DSL and confirm:
- No unsafe generation
- Self-limiting logic in modules
- Logs reviewed periodically
