import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    us_voices = [v for v in voices if v["Locale"] == "en-US"]
    print("Found en-US voices:")
    for v in us_voices:
        print(f"  {v['ShortName']} ({v['Gender']}) - {v.get('FriendlyName', '')}")

    # Test Christopher
    test_voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate("Construction progress you can trust. Welcome to SiteIQ.", test_voice)
    await communicate.save("test_christopher.mp3")
    print(f"Successfully generated test_christopher.mp3 with {test_voice}!")

if __name__ == "__main__":
    asyncio.run(main())
