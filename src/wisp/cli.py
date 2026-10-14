from __future__ import annotations

import argparse
import json

from .audio import AlsaPlayer, AlsaRecorder, CommandTextToSpeech, VoskFileSpeechToText
from .config import ConfigStore
from .models import Character
from .voice_pipeline import VoicePipeline
from .web import create_app
from .web.app import Runtime


def main() -> None:
    parser = argparse.ArgumentParser(prog="wisp", description="WISP local voice companion")
    parser.add_argument("--config", help="Path to config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve = subparsers.add_parser("serve", help="Run the local configuration panel")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    subparsers.add_parser("show-config", help="Print the effective configuration")
    voice_once = subparsers.add_parser("voice-once", help="Run one record/transcribe/respond/speak cycle")
    voice_once.add_argument("--seconds", type=int, help="Recording duration")
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
        audio = config["audio"]
        if audio.get("stt_provider") != "vosk-file" or audio.get("tts_provider") != "command":
            parser.error("voice-once requires stt_provider=vosk-file and tts_provider=command")
        runtime = Runtime(store)
        active = next(
            Character.from_dict(item)
            for item in config["characters"]
            if item["id"] == config["active_character_id"]
        )
        pipeline = VoicePipeline(
            AlsaRecorder(audio.get("input_device", ""), int(audio.get("sample_rate", 16_000))),
            VoskFileSpeechToText(audio["vosk_model"]),
            runtime.conversation(),
            CommandTextToSpeech(audio["tts_executable"], list(audio["tts_arguments"])),
            AlsaPlayer(audio.get("output_device", "")),
            config["paths"]["data_dir"],
        )
        result = pipeline.run_once(
            active, config["child"], args.seconds or int(audio.get("record_seconds", 6))
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

