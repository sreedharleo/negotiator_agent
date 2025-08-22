from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re
import math
import json

# Replace Concordia imports with plain classes
# from concordia.agents import AgentWithLogging
class AgentWithLogging:
    def __init__(self, name):
        self.name = name
    def log(self, message):
        print(f"[{self.name}] {message}")

# from concordia.components.entity import ContextComponent
class ContextComponent:
    def __init__(self):
        self.state = {}

# from concordia.associative_memory import associative_memory
class AssociativeMemory:
    def __init__(self):
        self.memory = {}

# from concordia.language_model import language_model
class LanguageModel:
    def generate(self, prompt):
        return f"Response to: {prompt}"


import requests

def query_llama(prompt: str) -> str:
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False,
        "max_tokens": 50  # short replies for negotiation
    }
    response = requests.post(url, json=data)
    return response.json()["response"]


# ----------------------------
# Domain models
# ----------------------------
@dataclass
class Product:
    name: str
    base_price: int  # reference price (e.g., MSRP or market avg)


@dataclass
class NegotiationResponse:
    action: str          # "accept" | "counter" | "reject" | "ask"
    message: str
    offer: Optional[int] = None


# ----------------------------
# Personality Component
# ----------------------------
class BuyerPersonalityComponent(ContextComponent):
    """
    Your agent's personality definition.
    Controls tone and concession style.
    """

    def __init__(self, personality_type: str = "neutral"):
        self.personality_type = personality_type
        # Tunable knobs per personality
        presets = {
            "aggressive": dict(opening_multiplier=0.60, concession_rate=0.07, accept_gap=0.04, tone="curt"),
            "frugal":     dict(opening_multiplier=0.70, concession_rate=0.09, accept_gap=0.06, tone="polite"),
            "friendly":   dict(opening_multiplier=0.80, concession_rate=0.12, accept_gap=0.10, tone="warm"),
            "neutral":    dict(opening_multiplier=0.75, concession_rate=0.10, accept_gap=0.08, tone="neutral"),
        }
        p = presets.get(personality_type, presets["neutral"])
        self.opening_multiplier = p["opening_multiplier"]
        self.concession_rate   = p["concession_rate"]
        self.accept_gap        = p["accept_gap"]
        self.tone              = p["tone"]

    def make_pre_act_value(self) -> str:
        """
        Provide personality context for the LLM (if you use it to phrase messages).
        """
        return (
            f"You are a buyer with a {self.personality_type} personality. "
            f"Tone is {self.tone}. Keep responses concise, constructive, and consistent. "
            f"Never exceed the given budget. Maintain steady concessions at ~{int(self.concession_rate*100)}% "
            f"of the gap per round. Accept if the remaining gap is within {int(self.accept_gap*100)}% and within budget."
        )

    def get_state(self) -> Dict[str, Any]:
        return {
            "personality_type": self.personality_type,
            "opening_multiplier": self.opening_multiplier,
            "concession_rate": self.concession_rate,
            "accept_gap": self.accept_gap,
            "tone": self.tone,
        }

    def set_state(self, state: Dict[str, Any]):
        self.personality_type  = state.get("personality_type", "neutral")
        self.opening_multiplier = state.get("opening_multiplier", 0.75)
        self.concession_rate    = state.get("concession_rate", 0.10)
        self.accept_gap         = state.get("accept_gap", 0.08)
        self.tone               = state.get("tone", "neutral")


# ----------------------------
# Memory Component
# ----------------------------
class BuyerMemoryComponent(ContextComponent):
    """
    Stores negotiation history. Wraps Concordia associative memory for retrieval.
    """
    def __init__(self):
        self._am = associative_memory.AssociativeMemory()
        self._history: List[Dict[str, Any]] = []  # plain timeline for quick scans

    def add_interaction(self, role: str, message: str, offer: Optional[int] = None):
        event = {"role": role, "message": message, "offer": offer}
        self._history.append(event)
        # Persist in Concordia memory (API may vary slightly; adjust if needed)
        try:
            self._am.add_item(json.dumps(event))
        except Exception:
            # Fallback: ignore if API differs in your build
            pass

    def last_offer(self, role: str) -> Optional[int]:
        for e in reversed(self._history):
            if e["role"] == role and e["offer"] is not None:
                return e["offer"]
        return None

    def rounds(self) -> int:
        # Count buyer turns as "rounds" (or total turns // 2 if you prefer)
        return sum(1 for e in self._history if e["role"] == "buyer")

    def get_state(self) -> Dict[str, Any]:
        return {"history": self._history}

    def set_state(self, state: Dict[str, Any]):
        self._history = state.get("history", [])


# ----------------------------
# Observation Component
# ----------------------------
class BuyerObservationComponent(ContextComponent):
    """
    Process seller messages and extract structured signals:
    - numeric offer
    - 'final' intent
    - shipping/bonus cues (naive)
    """
    _price_pattern = re.compile(r"(?:₹|\$|rs\.?\s*|inr\s*)?\s*(\d[\d,]*)(?:\.\d+)?", re.IGNORECASE)

    def process_message(self, message: str) -> Dict[str, Any]:
        # Extract first reasonable integer as the seller's price
        offer = None
        nums = self._price_pattern.findall(message)
        if nums:
            try:
                offer = int(nums[0].replace(",", ""))
            except Exception:
                offer = None

        msg_l = message.lower()
        is_final = any(kw in msg_l for kw in ["final", "last price", "take it or leave it", "firm"])
        extras   = {
            "includes_shipping": any(k in msg_l for k in ["free shipping", "delivery included", "including shipping"]),
            "bonus": any(k in msg_l for k in ["free case", "addon", "bundle", "accessory"]),
        }

        return {"seller_message": message, "seller_offer": offer, "is_final": is_final, **extras}

    def make_pre_act_value(self) -> str:
        return "You extract structured data from seller text: price (int), is_final (bool), extras."

    def get_state(self) -> Dict[str, Any]:
        return {}

    def set_state(self, state: Dict[str, Any]):
        pass


# ----------------------------
# Decision Component
# ----------------------------
class BuyerDecisionComponent(ContextComponent):
    """
    Core negotiation strategy. Guarantees never exceeding budget.
    """
    def __init__(self, budget: int, max_rounds: int = 6):
        self.budget = int(budget)
        self.max_rounds = max_rounds

    def _format_tone(self, base: str, tone: str) -> str:
        if tone == "curt":
            return base
        if tone == "warm":
            return base + " 🙂"
        if tone == "polite":
            return "Please " + base[0].lower() + base[1:]
        return base

    def _opening_counter(self, seller_offer: int, personality: BuyerPersonalityComponent) -> int:
        raw = int(math.floor(seller_offer * personality.opening_multiplier))
        return max(1, min(raw, self.budget))

    def _concede(self, last_buyer_offer: int, seller_offer: int, personality: BuyerPersonalityComponent) -> int:
        gap = max(0, min(seller_offer, self.budget) - last_buyer_offer)
        step = max(1, int(math.ceil(gap * personality.concession_rate)))
        nxt = last_buyer_offer + step
        return min(nxt, self.budget)

    def decide(
        self,
        product: Product,
        observation: Dict[str, Any],
        memory: BuyerMemoryComponent,
        personality: BuyerPersonalityComponent,
    ) -> NegotiationResponse:

        seller_offer = observation.get("seller_offer")
        is_final     = observation.get("is_final", False)
        rounds_so_far = memory.rounds()

        # No concrete price from seller → ask
        if not seller_offer:
            msg = self._format_tone(
                f"could you share your best price for the {product.name}?",
                personality.tone,
            )
            return NegotiationResponse(action="ask", message=msg)

        # If seller offer already within budget and gap small → accept
        last_buyer = memory.last_offer("buyer")
        # Compute acceptable threshold as percent of seller offer
        acceptable_gap = max(1, int(seller_offer * personality.accept_gap))

        if seller_offer <= self.budget:
            if last_buyer is None:
                # First move: check if seller is close to base price or budget
                if abs(seller_offer - min(self.budget, product.base_price)) <= acceptable_gap:
                    msg = self._format_tone(f"deal at {seller_offer}.", personality.tone)
                    return NegotiationResponse("accept", msg, seller_offer)
            else:
                if (seller_offer - last_buyer) <= acceptable_gap or is_final or rounds_so_far >= (self.max_rounds - 1):
                    msg = self._format_tone(f"deal at {seller_offer}.", personality.tone)
                    return NegotiationResponse("accept", msg, seller_offer)

        # If seller marks final and it's over budget → reject immediately
        if is_final and seller_offer > self.budget:
            msg = self._format_tone(
                "that's above my budget—I'll have to pass.",
                personality.tone,
            )
            return NegotiationResponse("reject", msg)

        # Opening counter
        if last_buyer is None:
            counter = self._opening_counter(seller_offer, personality)
        else:
            # Concede toward min(seller_offer, budget)
            counter = self._concede(last_buyer, seller_offer, personality)

        # Safety: never exceed budget
        counter = min(counter, self.budget)

        # If we ran out of rounds and still far → reject
        if rounds_so_far >= self.max_rounds and (seller_offer - counter) > acceptable_gap:
            msg = self._format_tone(
                f"I can't go higher than {counter}. If that doesn't work, I'll pass.",
                personality.tone,
            )
            return NegotiationResponse("reject", msg)

        # Normal counter
        msg = self._format_tone(
            f"that's a bit high. I can do {counter}.",
            personality.tone,
        )
        return NegotiationResponse("counter", msg, counter)

    def make_pre_act_value(self) -> str:
        return "You compute numeric offers strictly within budget, with bounded concessions and acceptance rules."

    def get_state(self) -> Dict[str, Any]:
        return {"budget": self.budget, "max_rounds": self.max_rounds}

    def set_state(self, state: Dict[str, Any]):
        self.budget = int(state.get("budget", self.budget))
        self.max_rounds = int(state.get("max_rounds", self.max_rounds))


# ----------------------------
# Agent wiring
# ----------------------------
class YourBuyerAgent:
    """
    Concordia-based Buyer Agent that maintains personality consistency,
    tracks history, parses seller messages, and applies a smart strategy.
    """

    def __init__(self, name: str, personality_type: str, model: LanguageModel, budget: int):
        self.name = name
        self.personality_type = personality_type
        self.model = model
        self.budget = int(budget)
        self._build_components()

    def _build_components(self):
        # Required Concordia components
        self.personality = BuyerPersonalityComponent(self.personality_type)
        self.memory      = BuyerMemoryComponent()
        self.observation = BuyerObservationComponent()
        self.decision    = BuyerDecisionComponent(self.budget)

        # Logging / trace (optional but helpful)
        self.logger = entity_agent_with_logging.EntityAgentWithLogging(self.name)

    def negotiate(self, product: Product, seller_message: str) -> NegotiationResponse:
        # Observe
        obs = self.observation.process_message(seller_message)

        # Decide
        result = self.decision.decide(product, obs, self.memory, self.personality)

        # Phrase message (optionally via LLM) while keeping numeric offer intact
        # NOTE: Keep the computed 'offer' authoritative (never let LLM change numbers beyond budget).
        try:
            sys = (
                self.personality.make_pre_act_value()
                + " Keep the numeric offer unchanged if provided. "
                  "Be concise and cooperative."
            )
            user = (
                f"Seller said: {seller_message}\n"
                f"Buyer action: {result.action}\n"
                f"Buyer offer (if any): {result.offer}\n"
                f"Draft a single-sentence reply with the same numeric offer."
            )
        except Exception:
            # If LLM not available, use the deterministic message
            pass
            
# Phrase message (optionally via LLM) while keeping numeric offer intact
        # NOTE: Keep the computed 'offer' authoritative (never let LLM change numbers beyond budget).
        try:
            prompt = (
                self.personality.make_pre_act_value()
                + " Keep the numeric offer unchanged if provided. "
                + "Be concise and cooperative.\n"
                + f"Seller said: {seller_message}\n"
                + f"Buyer action: {result.action}\n"
                + f"Buyer offer (if any): {result.offer}\n"
                + "Draft a single-sentence reply with the same numeric offer."
            )

            # Call Ollama LLaMA 3.1
            llm_reply = query_llama(prompt).strip()
            if llm_reply:
                result.message = llm_reply

        except Exception:
            # If LLM not available, use the deterministic message
            pass

        # Log + remember
        self.logger.log({"seller_message": seller_message, "decision": result.__dict__})
        self.memory.add_interaction("seller", seller_message, obs.get("seller_offer"))
        self.memory.add_interaction("buyer", result.message, result.offer)

        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "personality": self.personality.get_state(),
            "memory": self.memory.get_state(),
            "decision": self.decision.get_state(),
            "budget": self.budget,
        }

    def set_state(self, state: Dict[str, Any]):
        self.personality.set_state(state.get("personality", {}))
        self.memory.set_state(state.get("memory", {}))
        self.decision.set_state(state.get("decision", {}))
        self.budget = int(state.get("budget", self.budget))
