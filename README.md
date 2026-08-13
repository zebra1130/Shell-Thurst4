# Shell-Thurst4 — instrument control

Python code for driving the lab instruments used in our experiments, one
folder per device. Each folder is self-contained: its own README, its own
`config.py`, its own dependencies. Nothing in one device folder imports from
another, so you can use just the one you need and ignore the rest.

## Devices

| Folder | Device | What it does |
|---|---|---|
| [`turntable/`](turntable/) | ComXim intelligent / programmable turntable | Steps N samples through a Raman spectrometer over a chosen total angle, then returns to the start |

*(more devices to be added)*

## Getting started

Clone the repository, then follow the README inside the folder for the device
you are using:

```bash
git clone https://github.com/zebra1130/Shell-Thurst4.git
```

```bash
cd Shell-Thurst4/turntable
```

Python 3.8 or newer is required. Each device folder lists its own
dependencies in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Repository layout

```
Shell-Thurst4/
├── README.md          you are here — index of devices
├── LICENSE            MIT, applies to the whole repository
├── .gitignore
└── turntable/         ComXim turntable
    ├── README.md          full setup and operating guide
    ├── config.py          the only file you normally edit
    ├── raman_sequence.py  the measurement run
    ├── turntable_cli.py   manual control from a terminal
    ├── turntable.py       serial driver
    ├── examples/          minimal examples of each action
    ├── requirements.txt
    └── HARDWARE_AND_COMMANDS.md   command reference
```

## Adding a new device

1. Create a folder named after the device, e.g. `spectrometer/`.
2. Inside it, keep the same shape as `turntable/`: a driver module, a
   `config.py` holding everything a user would want to change, a runnable
   script, a `requirements.txt`, and a `README.md` that a newcomer can follow
   from top to bottom without asking questions.
3. Add a row to the **Devices** table above and a branch to the layout tree.
4. Keep device folders independent — no cross-imports. Shared helpers only
   earn a top-level `common/` package once two devices genuinely need the
   same code.

## Contributing

Issues and pull requests are welcome. Bug reports are most useful when they
say which instrument model you have and which step of the device README
failed.

## License

[MIT](LICENSE) — free to use, modify and redistribute, with attribution.

These are unofficial, independent tools and are not affiliated with or
endorsed by any instrument manufacturer. Motorised hardware can pinch, snag
cables and drop samples: test new sequences with nothing valuable mounted, and
keep the power switch within reach.
