# tinted-windows-terminal

Remote tinty template that builds a Windows Terminal color scheme named `Tinty`
per scheme (base16, base24, tinted8). The ANSI mapping matches tinted-shell, so
WSL tabs and pwsh tabs agree.

- `templates/`: one scheme object per system.
- `apply-scheme.py`: the tinty hook. It upserts the `Tinty` object into the
  `schemes` array of the Store WT `settings.json`. That file is JSONC, so the
  script edits it as text: comments and formatting elsewhere are preserved.
  The previous file is kept as `settings.json.tinty.bak`. WT hot-reloads.
- `themes/`: built output, one file per scheme (committed; tinty reads it directly).

WT settings fragments are not used (they don't load on this Store install).

## Development

Edit `templates/`, then preview locally:

```bash
tinty build .
```

Commit and push `templates/` and `themes/`. The
[update workflow](.github/workflows/update.yml) also rebuilds `themes/` on every
push touching `templates/` and weekly against the latest upstream schemes.
Users pick up changes with `tinty update`.

## Tinted Configuration

Append to `~/.config/tinted-theming/tinty/config.toml`:

```toml
[[items]]
name = "tinted-windows-terminal"
path = "https://github.com/jfishe/tinted-windows-terminal"
themes-dir = "themes"
hook = "python3 -I ~/.local/share/tinted-theming/tinty/repos/tinted-windows-terminal/apply-scheme.py %f"
supported-systems = ["base16", "base24", "tinted8"]
```

`settings.json` (one time): `profiles.defaults.colorScheme.dark = "Tinty"`.
