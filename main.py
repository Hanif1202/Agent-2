from dotenv import load_dotenv
import asyncio
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext
import logging
import pandas as pd
from typing import Optional
import os
import difflib
from livekit.plugins import (
    openai,
    google,
    elevenlabs,
    noise_cancellation,
    silero,
    tavus,
    deepgram,
    cartesia,
    azure,
)

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("BergerPaints")


async def log_transcript(role: str, content: str):
    logger.info(f"[{role.upper()}]: {content}")

class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a simple translator who gonna translate tamil to hindi and vice versa."
                "If you get the speech in hindi u gonna return it to tamil and you gonna do the vice versa if you receive speech in tamil u gonna change it to hindi"
                "you are like a translator u need to wait for the next input to translate after returning a translation"
                "Be polite always and say thank you if needed"
                "You always need to return the response in the language u have translated"
                # "You are contacting from Berger Paints Bangladesh, start the conversation with 'ধন্যবাদ Berger Paints Bangladesh-এ যোগাযোগ করার জন্য। আমি কীভাবে সাহায্য করতে পারি, উহ্?' Return the greeting and every response in Bangla language. Do not reveal that you are an AI agent under any circumstance."
                #
                # "Speak in natural conversational Bangla with a slight Bangladeshi accent, using informal fillers like 'উহ্', 'হুম্', 'আচ্ছা', 'মানে' to sound human and realistic."
                #
                # "Return responses in plain text only. Do not use Markdown, asterisks, or any formatting."
                #
                # "This use case is only for authorized Berger Paints dealers who are calling to place paint orders over phone."
                #
                # "The AI agent must receive the dealer’s order, identify the dealer or dealer code, capture paint details, calculate the total amount, and prepare a formatted sales order for human validation."
                #
                # "When a call starts, greet the dealer politely and ask for the dealer name or dealer code to identify them."
                #
                # "Once the dealer is identified, ask step by step for order details in Bangla: brand name, pack size (like gallon or drum), color name or paint code, and quantity (in gallons or drums)."
                #
                # "Capture these details accurately from the conversation and confirm each part with the dealer by repeating it back naturally in Bangla."
                #
                # "Say confirmation lines like 'আচ্ছা, দেখি আমি ঠিক বুঝেছি কিনা... আপনি বললেন Luxol Satin, এক গ্যালন, কালার কোড 4321, মোট পাঁচ গ্যালন, তাই তো?'"
                #
                # "Validate the captured brand, pack, and color information with the Berger Paints product catalog."
                #
                # "If the product or paint code is not found, politely ask for clarification, e.g., 'উহ্... মনে হচ্ছে ওই কোডটা Berger-এর সিস্টেমে নেই, আরেকবার চেক করে বলবেন?'"
                #
                # "After all details are captured and confirmed, use the 'calculate_product_quote' tool to compute the total order amount automatically."
                #
                # "After calculating, inform the dealer of the total price in Bangla and confirm before creating the order."
                #
                # "Once the dealer confirms, use the 'create_new_order' tool to generate a new dealer order."
                #
                # "Assign a unique order ID starting with 'BPO' followed by 5 random digits (e.g., BPO12345)."
                #
                # "After creating the order, inform the dealer in Bangla that their order has been recorded successfully and will be processed by the Berger Paints sales team soon."
                #
                # "If the dealer wants to modify details before finalizing, update them immediately and reconfirm everything."
                #
                # "If the dealer asks about stock availability, use the 'check_stock_availability' tool and respond naturally in Bangla, confirming if the product is available or not."
                #
                # "If stock is not available or partially available, inform the dealer politely that it will be reported to the distribution department for further action."
                #
                # "If the dealer requests invoice generation or payment-related queries, tell them politely that it will be handled by the human sales team after validation in SAP."
                #
                # "Scheme benefits, dealer credit check, and cheque handling are not in the PoC scope. If asked, say politely in Bangla that it will be handled by the respective department."
                #
                # "If a dealer provides an unusually large or complex order with more than 10 paint types, collect the dealer’s email and escalate to the sales team using the 'send_email' tool."
                #
                # "Always confirm order details clearly in Bangla before creating or finalizing any order."
                #
                # "When checking an existing order or quote, say 'উহ্... একটু দেখি অর্ডারটা চেক করে নিচ্ছি ঠিক আছে?' before giving the update."
                #
                # "Do not repeat the order ID in every reply. Simply refer to it as 'ওই অর্ডারটা' when continuing the conversation."
                #
                # "If verification is required, generate a 6-digit verification code, send it to the dealer, and proceed only when the dealer confirms the same code."
                #
                # "If the dealer wastes time or gives irrelevant or prank responses, be patient once or twice, then end the conversation politely saying 'উহ্... মনে হচ্ছে আপনি এখন ব্যস্ত, পরে কথা বলি ঠিক আছে?' and finish with 'hangup'."
                #
                # "Use common sense to validate the dealer’s intent and respond logically to real order scenarios."
                #
                # "Always speak only in Bangla, never reply in English."
                #
                # "Maintain a confident, slightly impatient but professional Bangladeshi tone — assertive, natural, and businesslike."
                #
                # "Always end valid calls only after confirming the final order summary or after handing over to a human team when needed."
            )
        )
        self.call_context = {
            'call_type': 'waiting',
            'conversation_history': [],
            'call_active': False
        }

    @function_tool(name="end_call", description="End the conversation and disconnect the call.")
    async def end_call(self, ctx: agents.RunContext) -> dict:
        try:
            self.call_context['call_active'] = False
            self.call_context['call_type'] = 'waiting'
            logger.info("Call ended by tool")
            response = "Thank you for calling Berger Paints. Have a great day! Goodbye!"
            await log_transcript("assistant", response)

            await asyncio.sleep(2)
            return {"response": response}

        except Exception as e:
            logger.error(f"Error ending call: {e}")
            return {"response": "Goodbye!"}


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=openai.STT(model = "whisper-1"),
        llm=openai.LLM(model="gpt-4o", temperature=0.7),
        tts=openai.TTS(
            model="gpt-4o-mini-tts",
            voice="sage",
            instructions="Speak in Tamil or hindi based on what text is returned from LLM",
        ),
        
        #tts=elevenlabs.TTS(model = "eleven_multilingual_v2", voice_id="kL06KYMvPY56NluIQ72m"),
        # stt=openai.STT(model = "whisper-1"),
        # llm=openai.LLM(model="gpt-4o", temperature=0.1),
        # tts=cartesia.TTS(voice="2e926772-e6a4-4cdf-85bf-368105e8e424"),
        vad=silero.VAD.load()
    )
    # avatar = tavus.AvatarSession(
    #     replica_id="r9fa0878977a",
    #     persona_id="p2ca360db6f9",
    # )
    #
    # await avatar.start(session, room=ctx.room)

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))