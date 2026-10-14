# Ricognizione del dispositivo di origine

Ricognizione eseguita il 14 ottobre 2026 in sola lettura. La memoria eMMC è stata montata con opzioni `ro,norecovery` e smontata al termine.

## Sistema

| Voce | Valore osservato |
|---|---|
| SoC | Rockchip RK3566, 4 × Cortex-A55 fino a 1,8 GHz |
| RAM | 3,8 GiB visibili, swap zram 1,9 GiB |
| Sistema | Armbian community / Ubuntu ARM64 |
| Kernel | Linux 6.18.44-current-rockchip64 |
| Root filesystem | ext4 da 7,1 GiB, 97% occupato |
| Memoria dati | eMMC F2FS da 25,1 GiB, non montata automaticamente |

La root disponeva di circa 248 MiB liberi. Per questo i file di deployment WISP usano `/mnt/emmc/wisp` e non `/opt/wisp`.

## Componenti AI

- `llama.cpp` build 10586, commit `b21e4de74567f5eef213765c9476a843c2e43f0d`;
- Qwen 2.5 1.5B Instruct Q4_K_M;
- embedding `paraphrase-multilingual-MiniLM-L12-v2`, ONNX quantizzato, vettori da 384 dimensioni;
- reranker basato su `mMiniLMv2-L12-H384-distilled-from-XLMR-Large`, ONNX quantizzato;
- indice NPZ con 181 frammenti: 124 provenienti da contenuti personali e 57 dal mondo del personaggio;
- retrieval ibrido: similarità vettoriale, punteggio lessicale e reranking.

Il benchmark archiviato riportava 61 risposte corrette su 69 casi noti (88,4%), con 1,047 secondi medi per il retrieval. Corpus e output non sono inclusi perché contengono dati privati e contenuti non redistribuibili.

## Stato dei servizi

- Nessun servizio WISP, Qwen, RAG o audio era attivo.
- `llama-server` veniva avviato manualmente su `127.0.0.1:8080`.
- Nessuna unit systemd dedicata e nessun avvio automatico erano presenti.
- Nessuna porta applicativa era in ascolto oltre ai servizi di sistema.

## Audio

- `arecord -l` non mostrava dispositivi di acquisizione.
- `aplay -l` mostrava soltanto HDMI e SPDIF.
- PulseAudio non accettava connessioni nella sessione SSH.
- Era presente una build di Whisper, ma non risultava collegata alla conversazione.
- Vosk era stato provato su file WAV registrati in precedenza.
- Non è stato trovato un motore TTS operativo o distribuibile.

Di conseguenza la pipeline vocale di WISP è implementata come composizione di provider, ma deve ancora essere verificata con il microfono reale e una voce autorizzata.

## Vincoli mantenuti

- Nessun file del prototipo è stato modificato.
- Nessun servizio è stato avviato, arrestato o riavviato.
- Modelli, registrazioni, corpus privato e dati del bambino non sono entrati nella repository.
- L’eMMC è tornata non montata al termine di ogni sessione di analisi o copia.

