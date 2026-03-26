# Global Rules

- OS: Ubuntu 24.04 (WSL2), RTX 5090, Python 3.12, CUDA 13.1(12.8も併用), TensorRT 10.15, uv使え
- 全知識は `~/.claude/memory.db` (FTS5)。LIKEは禁止
- 検索: `SELECT source_table, substr(text,1,150) FROM memory_fts WHERE memory_fts MATCH 'keyword' LIMIT 10`
- 新サービス作成時 → services INSERT必須。新ルール発見時 → rules INSERT + FTS再構築
- DB情報(services, rules, memories)は変更即更新。古い情報は即座に修正せよ
- ポートは `ss -tlnp | grep LISTEN` で実状確認してから決定。競合・横取り絶対禁止
- 全サービスが本番環境。運用マニュアル: ~/Downloads/manuals/ACTIVE_OPERATIONS_MANUAL_LATEST.txt
- 頼まれたことだけやれ。勝手に追加変更するな。「ついでに」やるな
- 設計意図がわからないコードを安易に「改善」するな。まず聞け
- Geminiモデル名: gemini-2.5-flash, gemini-2.5-pro, gemini-3-flash-preview, gemini-3.1-pro-preview

# LLMパイプライン戦略
- 前処理（大量データの粗い抽出）: ローカルNemotron 9B（localhost:8000, 無制限, 速い, 精度低め）
- 整理・品質向上（クリーニング・分類・補完）: Gemini CLI（無料枠を毎日使い切る, 高精度）
- Gemini CLIにはDB+元データを渡して「自分で見て判断して直せ」と指示するのが効率的
- Claude Codeは設計・コード・アーキテクチャ判断担当。力仕事はNemotron/Geminiに回す
- Gemini CLI無料枠: 1日1,000リクエスト, 60RPM, 100万トークンコンテキスト。モデルはGemini 3.1 Pro。毎日使い切れ
