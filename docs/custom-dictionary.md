# Custom Dictionary

The custom dictionary lets you teach Aside domain-specific terms and correction rules. It handles things Whisper consistently gets wrong for your use case — product names, technical jargon, proper nouns, and abbreviations.

## Where the File Lives

```
~/.aside/dictionary.txt
```

Aside watches this file and reloads it automatically when you save changes. You can also add terms through the in-app Settings panel under "Custom Dictionary".

## File Format

```
# Lines starting with # are comments — ignored by the parser

# Hotwords: terms Aside should bias toward recognizing
FastAPI
LightGBM
PyTorch

# Replacements: correct what Whisper gets wrong
# Format: wrong text → correct text
whisper dictation → Aside
new neural net → neural network
graph Q L → GraphQL
kubernetes → Kubernetes
```

- Blank lines are ignored
- The `→` delimiter separates the pattern from the replacement (plain ASCII `->` also works)
- Matching is case-insensitive for patterns; replacements are applied as written
- The file is UTF-8 encoded

## 50-Term Cap

The dictionary supports up to 50 entries (hotwords + replacements combined). This limit exists because Whisper's `initial_prompt` parameter has a token budget. Entries beyond 50 are silently ignored — the in-app editor shows a count so you can stay under the limit.

## How to Add Terms

**In-app:** Open Aside settings (click the menubar icon → Settings → Custom Dictionary). Use the text fields to add a hotword or a replacement rule. Changes save immediately.

**By editing the file directly:** Open `~/.aside/dictionary.txt` in any text editor and save. Aside reloads within a few seconds.

## Example Dictionary File

```
# Company and product names
Acme Corp
WidgetOS
DataPipeline Pro

# Technical terms
WebAssembly
k8s → Kubernetes
postgres → PostgreSQL
js → JavaScript
ts → TypeScript
api → API
ui → UI
ux → UX

# People
Kai
Lauren

# Domain replacements
to do → TODO
pick a rest → Pickerest
```

## How the Three Layers Work

Aside applies the dictionary at three points in the pipeline:

1. **Hotwords parameter** — Hotwords are passed to `faster-whisper` as `hotwords`. This biases the model's beam search toward those tokens, making Whisper more likely to output them when the audio is ambiguous.

2. **Initial prompt** — All dictionary terms are also serialized into Whisper's `initial_prompt` parameter. This gives the model prior context about your vocabulary before it processes your audio.

3. **Post-processing** — After Whisper produces a transcript, Aside applies replacement rules in order. This catches cases where the hotword bias wasn't enough — the wrong text is simply swapped for the correct text before injection.
