name: VFS Monitor
on:
  schedule:
    - cron: '*/3 * * * *'
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run monitor
        env:
          TOKEN: ${{ secrets.TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
          TLS_EMAIL: ${{ secrets.TLS_EMAIL }}
          TLS_PASSWORD: ${{ secrets.TLS_PASSWORD }}
        run: python monitor.py
