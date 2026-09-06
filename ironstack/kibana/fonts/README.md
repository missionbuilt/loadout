# Brand faces, subset for embedding

Oswald 500/700, JetBrains Mono 400/500, Merriweather 400. All three are under the SIL
Open Font License 1.1 (embedding and redistribution permitted; the fonts may not be sold
on their own). Sources: the `@fontsource/oswald`, `@fontsource/jetbrains-mono` and
`@fontsource/merriweather` npm packages, latin subsets, cut further with

    pyftsubset <latin.woff2> --flavor=woff2 --layout-features='*' \
      --unicodes="U+0020-007E,U+00A0-00FF,U+2013-2014,U+2018-201D,U+2022,U+2026,U+2190-2193,U+2212,U+25B8,U+25AE,U+00D7"

101 KB across the five. A custom content panel fetches nothing, so the only way a brand
face reaches a card is as a base64 `@font-face` inside the template. `probe_phase0.py`
is the test of whether the sandbox allows that at all; `templates.py` embeds them only
once it has said yes.
