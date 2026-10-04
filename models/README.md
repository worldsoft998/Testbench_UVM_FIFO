# Models

Trained RL policies are written here by `python -m aidvo.cli train`:

```text
models/
├── ppo/
│   ├── final.zip              # saved stable-baselines3 model
│   ├── train_meta.json        # algo, timesteps, workers, seed, action-space size
│   └── checkpoints/           # periodic checkpoints during training
├── a2c/...
└── dqn/...
```

* Training is **entirely local** (stable-baselines3 + PyTorch); no external
  AI model API is contacted.
* Evaluate with:
  `python -m aidvo.cli rollout -c config/aidvo_config.yaml --model models/ppo/final ...`
* Policies are specific to the knob layout in `config/aidvo_config.yaml` —
  retrain after changing the action space (the CLI will refuse a mismatched
  model rather than steering incorrectly).
