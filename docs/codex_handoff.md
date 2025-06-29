# Codex Training Handoff

**Purpose:**  
Wire up end-to-end automated training of the Silhouette model via your pre-configured Hugging Face Space and CI, so that pushes to `main` (or `train/*`) trigger a full training cycle, publish to the Hub, and allow manual kick-offs via the Space’s UI.

---

## 📂 Repo Layout

```

/.
├─ spaces/
│  └─ train_silhouette/        ← existing HF Space folder
│     ├─ app.py                ← Gradio UI to start training
│     ├─ train_silhouette.py   ← wrapper calling training/train_silhouette.py
│     └─ requirements.txt      ← accelerate, transformers, huggingface_hub, gradio, psutil
├─ training/
│  └─ train_silhouette.py      ← core training script
├─ config/
│  └─ train_config.yaml
├─ .github/
│  └─ workflows/
│     └─ train.yml            ← CI workflow for auto-training
└─ docs/
└─ codex_handoff.md         ← you are editing this

````

---

## 🔧 What Codex Must Do

1. **Populate the existing Space folder**  
   - Under `spaces/train_silhouette/` commit:  
     - `app.py` – a Gradio app that exposes a “Start Training” button and streams logs.  
     - `train_silhouette.py` – imports or shells out to `training/train_silhouette.py` using `../config/train_config.yaml`.  
     - `requirements.txt` with:
       ```
       accelerate
       transformers
       huggingface_hub
       gradio
       psutil
       ```
2. **Add the CI workflow**  
   Create or overwrite `.github/workflows/train.yml`:
   ```yaml
   name: Auto-Train & Publish

   on:
     push:
       branches: [ main, 'train/*' ]

   jobs:
     train:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.10'
         - run: |
             python -m venv .venv
             source .venv/bin/activate
             pip install -r requirements.txt -r requirements-dev.txt
             pip install accelerate huggingface_hub
         - run: |
             accelerate config default --yes
         - run: |
             accelerate launch \
               --num_processes 1 \
               --num_machines 1 \
               --mixed_precision no \
               --dynamo_backend no \
               --cpu \
               training/train_silhouette.py \
                 --config config/train_config.yaml
         - run: |
             accelerate upload outputs/checkpoints/best \
               --repo_id your-username/silhouette-core
````

3. **Use your existing Hugging Face Space**

   * Ensure that the `spaces/train_silhouette` folder is already connected to your pre-configured Space on HF.
   * No new Space creation is required—just commit these updates and push.

4. **Testing & Monitoring**

   * **Manual kick-off**: visit your existing Space’s URL, click **Start Training**, and watch logs.
   * **CI automation**: every push to `main` or `train/*` runs training + publish.
   * **Model versions**: check the Hub for new checkpoints and metrics.

---

## ⚙️ Final Codex Prompt

```
You are Codex. Your task:

1. Overwrite `docs/codex_handoff.md` with the updated instructions above.
2. Populate `spaces/train_silhouette/` (existing HF Space folder) with:
   - `app.py`
   - `train_silhouette.py`
   - `requirements.txt`
3. Add `.github/workflows/train.yml` exactly as specified.
4. Push all changes to a new branch `codex/training-pipeline`.
5. Open a PR so CI can validate and, upon merge, trigger the first automated run.
```

Once this is in place, your existing Space will drive both manual and CI-driven model training without creating anything new. Let me know if you need any tweaks!
