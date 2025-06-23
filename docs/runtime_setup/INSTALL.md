# Runtime Setup

1. Install llama.cpp:
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make
```
2. Download a GGUF model:
```bash
wget <model-url>
```
3. Run:
```bash
./main -m <model-name>.gguf -p "Hello"
```