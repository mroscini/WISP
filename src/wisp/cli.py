from __future__ import annotations

import argparse
import json
import sys

from .audio import AlsaPlayer, AlsaRecorder, CommandTextToSpeech, VoskFileSpeechToText
from .config import ConfigStore
from .button import watch_gpio_button
from .models import Character
from .voice_pipeline import VoicePipeline
from .web import create_app
from .web.app import Runtime


def _voice_pipeline(store: ConfigStore, runtime: Runtime, seconds: int | None = None):
    config = store.load()
    audio = config["audio"]
    if audio.get("stt_provider") != "vosk-file":
        raise RuntimeError("Configura audio.stt_provider come vosk-file")
    active = next(
        Character.from_dict(item)
        for item in config["characters"]
        if item["id"] == config["active_character_id"]
    )
    if active.voice_id == "command":
        tts = CommandTextToSpeech(audio["tts_executable"], list(audio["tts_arguments"]))
    elif active.voice_id == "disabled":
        raise RuntimeError("Scegli prima una voce per l'amico attivo")
    else:
        tts = runtime.voices.synthesizer(active.voice_id)
    pipeline = VoicePipeline(
        AlsaRecorder(audio.get("input_device", ""), int(audio.get("sample_rate", 16_000))),
        VoskFileSpeechToText(audio["vosk_model"]),
        runtime.conversation(),
        tts,
        AlsaPlayer(audio.get("output_device", "")),
        config["paths"]["data_dir"],
    )
    return pipeline, active, config, seconds or int(audio.get("record_seconds", 6))


def main() -> None:
    parser = argparse.ArgumentParser(prog="wisp", description="WISP local conversational device")
    parser.add_argument("--config", help="Path to config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve = subparsers.add_parser("serve", help="Run the local configuration panel")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    subparsers.add_parser("show-config", help="Print the effective configuration")
    voice_once = subparsers.add_parser("voice-once", help="Run one record/transcribe/respond/speak cycle")
    voice_once.add_argument("--seconds", type=int, help="Recording duration")
    subparsers.add_parser("button-service", help="Wait for a physical GPIO button and run conversations")
    args = parser.parse_args()

    store = ConfigStore(args.config)
    config = store.ensure()
    if args.command == "show-config":
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return
    if args.command == "serve":
        host = args.host or config["server"]["host"]
        port = args.port or int(config["server"]["port"])
        create_app(store.path).run(host=host, port=port, debug=False)
        return
    if args.command == "voice-once":
        runtime = Runtime(store)
        pipeline, active, current, seconds = _voice_pipeline(store, runtime, args.seconds)
        result = pipeline.run_once(active, current["child"], seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "button-service":
        button = config.get("button", {})
        if button.get("line") is None:
            parser.error("Configura button.line con l'offset GPIO del pulsante fisico")
        runtime = Runtime(store)

        def converse() -> None:
            try:
                pipeline, active, current, seconds = _voice_pipeline(store, runtime)
                result = pipeline.run_once(active, current["child"], seconds)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            except Exception as error:  # keep the hardware service alive after a failed turn
                print(f"WISP conversation failed: {error}", file=sys.stderr, flush=True)

        watch_gpio_button(
            str(button.get("chip", "/dev/gpiochip0")),
            int(button["line"]),
            converse,
            edge=str(button.get("edge", "falling")),
            debounce_ms=int(button.get("debounce_ms", 80)),
        )


if __name__ == "__main__":
    main()

