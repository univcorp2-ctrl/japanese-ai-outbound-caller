# 日本語AI電話サービス徹底調査

調査日: 2026-07-03

## 結論

最も現実的なのは、**LiveKit AgentsをOSSの制御層として使い、LiveKit SIPとSIPキャリアで
発信し、GPT-Realtime-2を日本語の音声対音声モデルとして接続する構成**です。自社コードを
保ちながら、文脈理解、割り込み、低遅延、ツール呼び出し、転送をまとめやすいためです。

Typelessは高品質な音声入力・文章整形製品であり、電話エージェントそのものではありません。
電話では8 kHz帯域、雑音、相槌、割り込み、無音、留守電が加わるため、文字起こし精度だけで
なくターン検出と応答開始遅延を分けて評価する必要があります。

## OSS候補

| 候補 | 発信 | 日本語 | 特徴 | 判定 |
|---|---:|---:|---|---|
| LiveKit Agents + SIP | 対応 | 接続モデル次第 | Agent、SIP、転送、テスト、self-host | 第一候補 |
| Pipecat | 対応 | 接続サービス次第 | STT/LLM/TTSの交換性が高い | 第二候補 |
| Vocode | 対応 | 接続サービス次第 | 電話Agentの既成部品 | 評価対象 |
| TEN Framework | 構成可 | 接続サービス次第 | realtime、VAD、拡張性 | 評価対象 |
| Siphon | 構成可 | 要検証 | 新しいOSS音声Agent基盤 | 成熟度確認 |
| Whisper/Kotoba + VOICEVOX | PBX併用 | 強い | 完全OSS寄り、データ主権 | 運用負荷大 |

LiveKitの公式アウトバウンド例はSIP participant作成、応答待ち、留守電処理、予定調整、転送を
示しています。PipecatはTwilio/Daily等の電話経路とストリーミング音声パイプラインを構成
します。完全OSSではAsterisk/Jambonz等のPBX/SIP、Kotoba-WhisperまたはWhisper、ローカル
LLM、VOICEVOXを組み合わせられますが、遅延最適化、GPU、エコー、監視が自社責任です。

## 商用候補

| サービス | 発信 | 日本語の組み方 | 主な技術 |
|---|---:|---|---|
| OpenAI Realtime + SIP/LiveKit | 対応 | GPT-Realtime-2 | native speech-to-speech、tools |
| Retell AI | 対応 | multilingual Agent、STT選択 | telephony orchestration、LLM、TTS |
| Vapi | 対応 | Deepgram/Google/Gladia等 | STT/LLM/TTS交換型 |
| ElevenLabs Agents | 対応 | 日本語TTS、Twilio/SIP | TTS、conversation Agent、tools |
| Bland AI | 対応 | language設定 | outbound API、conversation path |
| Deepgram Voice Agent | 経路連携 | Flux等の日本語STT | STT、turn detection、Agent API |

クラウド型は最短で本番化できますが、従量課金、国外処理、vendor lock-in、モデル更新による
品質変動を管理する必要があります。日本の実電話回線で、同一台本、同一雑音、同一番号・
固有語セットを用いた比較試験が必要です。

## 推奨3構成

### A. 品質優先

LiveKit Agents + LiveKit SIP + 対応SIP carrier + GPT-Realtime-2。音声の抑揚や間をテキスト化
せず保持しやすく、割り込みとtool callingを低遅延で扱えます。本リポジトリの標準です。

### B. 監査性・文章整形優先

LiveKit/Pipecat + Deepgram FluxまたはAzure STT + text LLM + ElevenLabs日本語TTS。全発話を
テキストで検査・redactionしやすく、Typeless的な言い直し除去・固有語補正をLLM段で実装
できます。一方、段数が増えて遅延と障害点が増えます。

### C. 完全OSS・on-prem優先

Asterisk/Jambonz + LiveKit/Pipecat + Kotoba-Whisper/Whisper + local LLM + VOICEVOX。外部送信を
抑えられますが、GPU、streaming、echo、barge-in、scale、monitoringを自社運用します。
VOICEVOXはengineだけでなく各characterの利用規約確認が必要です。

## 日本語品質の評価項目

- 電話帯域・雑音下の固有名詞、数字、日付、住所
- 相槌をターン終了と誤認しないこと
- 500–1000 ms程度を目標にした初回音声開始
- 割り込み時の即時停止と文脈維持
- 敬語、一文の短さ、確認復唱
- 留守電、人間、FAX、無音の判定
- 「不要」「止めて」等の多様な拒否表現
- tool実行前後の復唱と失敗時の安全なfallback

## 法務・運用

日本で勧誘目的の電話を行う場合、事業者名、担当者名、商品・サービスの種類、勧誘目的を
事前に伝え、拒否後の継続・再勧誘を行わない設計が必要です。録音や識別可能な会話データは
個人情報となり得るため、利用目的、通知、公表、保存期間、削除、access controlを定義します。
本実装は無差別発信ではなく、明示的opt-in、依頼された折返し、既存顧客、取引通知に限定します。

## 一次情報

1. LiveKit Agents: https://github.com/livekit/agents
2. LiveKit telephony: https://docs.livekit.io/agents/start/telephony/
3. LiveKit outbound example: https://github.com/livekit-examples/outbound-caller-python
4. Pipecat: https://github.com/pipecat-ai/pipecat
5. OpenAI GPT-Realtime-2: https://platform.openai.com/docs/models/gpt-realtime-2
6. OpenAI Realtime SIP: https://platform.openai.com/docs/guides/realtime-sip
7. OpenAI Voice Agents: https://platform.openai.com/docs/guides/voice-agents
8. Typeless: https://www.typeless.com/
9. Retell international calls: https://docs.retellai.com/deploy/international-call
10. Vapi multilingual: https://docs.vapi.ai/customization/multilingual
11. ElevenLabs Japanese TTS: https://elevenlabs.io/text-to-speech/japanese
12. Whisper: https://github.com/openai/whisper
13. Kotoba-Whisper: https://huggingface.co/kotoba-tech/kotoba-whisper-v2.0
14. VOICEVOX Engine: https://github.com/VOICEVOX/voicevox_engine
15. 消費者庁 電話勧誘販売: https://www.no-trouble.caa.go.jp/what/telemarketing/
16. 個人情報保護委員会 FAQ: https://www.ppc.go.jp/all_faq_index/faq1-q4-3/
17. Notion API create page: https://developers.notion.com/reference/post-page

リンク、価格、対応言語、licenseは変更されるため、本番採用時に一次情報を再確認してください。
