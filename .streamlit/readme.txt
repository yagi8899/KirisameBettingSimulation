config.tomlに以下を追加するとファイル監視をポーリングに強制する

[server]
fileWatcherType = "poll"
runOnSave = true

Windows では watchdog が壊れることが多く、polling 指定でほぼ100%復活します。