# Dal prototipo originale a WISP

Questa tabella distingue ciò che era realmente presente sul dispositivo dalle parti introdotte nella copia pubblicabile.

| Area | Prototipo RK3566 | WISP 0.1 |
|---|---|---|
| LLM | Qwen 2.5 1.5B tramite `llama-server` | Stessa API locale, configurabile |
| Embedding | MiniLM multilingue ONNX quantizzato | Stesso approccio, incapsulato in un provider |
| Retrieval | Similarità vettoriale + lessicale | Conservato e reso testabile |
| Reranking | mMiniLMv2 ONNX | Conservato e configurabile |
| Contenuti | Due file privati hardcoded | Documenti UTF-8 gestiti dal pannello |
| Personaggio | Identità e prompt hardcoded | Profili multipli persistenti |
| Interfaccia | REPL da terminale | Pannello web responsive sulla LAN |
| STT | Prove offline su file con Vosk; build Whisper presente | Adattatore Vosk e pipeline ALSA configurabile; hardware ancora da verificare |
| TTS | Non trovato sul dispositivo | Interfaccia disabilitata e adattatore a comando locale |
| Servizi | Nessun servizio del prototipo | Unit file di esempio, non installate automaticamente |
| Sicurezza web | Non applicabile | Upload limitati, path validati, header difensivi; autenticazione disattivata per scelta progettuale |

## Dati esclusi

- nome e informazioni personali del bambino;
- registrazioni e conversazioni;
- modelli o checkpoint vocali;
- il modello GGUF personalizzato sul personaggio;
- testi e storie protetti;
- credenziali e dettagli di rete privati.

Il profilo “Spider-Man” incluso nella configurazione di esempio è solo testo configurabile. Il progetto non include immagini, audio, storie, loghi o modelli ufficiali e non è affiliato a Marvel o Disney.

