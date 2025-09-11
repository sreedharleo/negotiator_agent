# Key improvements for your buyer agent implementation
# ...existing code...
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Minimal stubs and helpers (place these BEFORE test_scenarios and BEFORE ImprovedBuyerDecisionComponent)
class ContextComponent:
    pass

@dataclass
class Product:
    name: str
    market_price: int

@dataclass
class AgentResponse:
    message: str
    offer: Optional[int] = None
    action: str = "counter"  # 'accept', 'reject', 'counter'

class BuyerMemoryComponent:
    def __init__(self):
        self._round = 0
    def increment_round(self):
        self._round += 1
    def get_round_count(self) -> int:
        return self._round

class BuyerPersonalityComponent:
    def __init__(self, personality_type: str):
        self.personality_type = personality_type
        self.concession_rate = {
            "aggressive": 0.10,
            "diplomatic": 0.20,
            "analytical": 0.15
        }.get(personality_type, 0.15)

class YourBuyerAgent:
    def __init__(self, name: str, personality_type: str, budget: int):
        self.name = name
        self.personality = BuyerPersonalityComponent(personality_type)
        self.budget = int(budget)
        self.decision = None
        self.memory = BuyerMemoryComponent()
        self.last_offer: Optional[int] = None

    def attach_decision_component(self, decision_component):
        self.decision = decision_component

    def negotiate(self, product: Product, seller_msg: str) -> AgentResponse:
        # extract numeric price (handles comma separators)
        matches = re.findall(r'\d[\d,]*', seller_msg)
        if matches:
    # Clean up commas and convert all to ints
            nums = [int(m.replace(',', '')) for m in matches]
    # Assume seller offer is the largest number (price > quantity)
            seller_offer = max(nums)
        else:
            seller_offer = None


        observation = {
            "is_final_offer": any(k in seller_msg.lower() for k in ("final", "last offer", "take it or leave it"))
        }

        # advance round
        self.memory.increment_round()
        current_round = self.memory.get_round_count()

        if seller_offer is None:
            return AgentResponse("No price found in seller message", None, "counter")

        # lazy attach decision component if not provided (ImprovedBuyerDecisionComponent may be defined later)
        if self.decision is None:
            try:
                self.decision = ImprovedBuyerDecisionComponent(self.budget)
            except NameError:
                # fallback conservative counter if decision class not yet available
                counter = max(5000, int(self.budget * 0.8))
                self.last_offer = counter
                return AgentResponse(f"Counter offer ₹{counter:,}", counter, "counter")

                # Check if we should accept the seller's offer
        if self.decision._should_accept(seller_offer, observation, self.memory, self.personality):
            base_message = f"Accepting ₹{seller_offer:,}"
            context = "final" if observation.get("is_final_offer") else "respect"
            personality_message = generate_personality_message(
                base_message,
                self.personality.personality_type,
                context
            )
            return AgentResponse(personality_message, seller_offer, "accept")

        # Otherwise calculate a counter offer
        counter = self.decision._calculate_counter_offer(
            seller_offer,
            self.last_offer,
            self.personality,
            current_round
        )
        self.last_offer = counter

        # Pick context depending on personality
        context = (
            "pressure" if self.personality.personality_type == "aggressive" else
            "collaboration" if self.personality.personality_type == "diplomatic" else
            "data"
        )
        base_message = f"Counter offer ₹{counter:,}"
        personality_message = generate_personality_message(
            base_message,
            self.personality.personality_type,
            context
        )
        return AgentResponse(personality_message, counter, "counter")


# 1. Fix the incomplete test_scenarios function
def test_scenarios():
    """Complete test function for the 3 project scenarios"""
    
    scenarios = [
        {
            "name": "Easy Market",
            "product": Product("100 boxes Grade-A Alphonso Mangoes", 180000),
            "budget": 200000,
            "seller_messages": [
                "I have excellent Grade-A Alphonso mangoes. My price is ₹1,85,000 for 100 boxes.",
                "I can come down to ₹1,75,000 - that's my best offer.",
                "Final price: ₹1,65,000. Take it or leave it!"
            ]
        },
        {
            "name": "Tight Budget", 
            "product": Product("150 boxes Grade-B Kesar Mangoes", 150000),
            "budget": 140000,
            "seller_messages": [
                "150 boxes of premium Kesar mangoes for ₹1,55,000.",
                "I can do ₹1,45,000 if you're serious.",
                "My final offer is ₹1,35,000 - this is below my usual price."
            ]
        },
        {
            "name": "Premium Product",
            "product": Product("50 boxes Export-Grade Mangoes", 200000), 
            "budget": 190000,
            "seller_messages": [
                "These are export-quality mangoes. Price is ₹2,05,000 for 50 boxes.",
                "For a serious buyer, I can do ₹1,95,000.",
                "Last offer: ₹1,88,000 - this is premium quality at wholesale price."
            ]
        }
    ]
    
    personalities = ["aggressive", "diplomatic", "analytical"]
    
    for personality in personalities:
        print(f"\n{'='*60}")
        print(f"TESTING {personality.upper()} BUYER AGENT")
        print(f"{'='*60}")
        
        results = []
        
        for scenario in scenarios:
            print(f"\n--- {scenario['name']} Scenario ---")
            
            agent = YourBuyerAgent(
                name=f"{personality.title()}Buyer",
                personality_type=personality,
                budget=scenario["budget"]
            )
            
            print(f"Product: {scenario['product'].name}")
            print(f"Market Price: ₹{scenario['product'].market_price:,}")
            print(f"Budget: ₹{scenario['budget']:,}")
            print()
            
            final_result = None
            
            for i, seller_msg in enumerate(scenario["seller_messages"], 1):
                print(f"Round {i}")
                print(f"Seller: {seller_msg}")
                
                response = agent.negotiate(scenario["product"], seller_msg)
                
                print(f"Buyer ({personality}): {response.message}")
                if response.offer:
                    print(f"Buyer Offer: ₹{response.offer:,}")
                print(f"Action: {response.action}")
                print("-" * 40)
                
                if response.action in ["accept", "reject"]:
                    final_result = response
                    break
            
            # Calculate results
            if final_result:
                if final_result.action == "accept":
                    savings = scenario["budget"] - final_result.offer
                    savings_pct = (savings / scenario["budget"]) * 100
                    print(f"✅ DEAL CLOSED: ₹{final_result.offer:,}")
                    print(f"💰 Savings: ₹{savings:,} ({savings_pct:.1f}%)")
                else:
                    print("❌ DEAL REJECTED")
                    
                results.append({
                    "scenario": scenario["name"],
                    "success": final_result.action == "accept",
                    "final_price": final_result.offer if final_result.action == "accept" else None,
                    "savings": savings if final_result.action == "accept" else 0
                })
        
        # Summary for this personality
        successful_deals = sum(1 for r in results if r["success"])
        total_savings = sum(r["savings"] for r in results if r["success"])
        
        print(f"\n🎯 {personality.upper()} AGENT SUMMARY:")
        print(f"Successful Deals: {successful_deals}/3")
        print(f"Total Savings: ₹{total_savings:,}")
        print(f"Pass Threshold: {'✅ PASS' if successful_deals >= 2 else '❌ FAIL'}")

# 2. Enhanced decision logic for better negotiation outcomes
class ImprovedBuyerDecisionComponent(ContextComponent):
    """Enhanced decision component with better strategy"""
    
    def __init__(self, budget: int, max_rounds: int = 10):
        super().__init__()
        self.budget = int(budget)
        self.max_rounds = max_rounds
        self.min_savings_target = 0.10  # Target at least 10% savings
        self.desperation_threshold = 8  # Round at which to get desperate

    def _should_accept(
        self, 
        seller_offer: int, 
        observation: Dict[str, Any], 
        memory: BuyerMemoryComponent, 
        personality: BuyerPersonalityComponent
    ) -> bool:
        """Improved acceptance logic"""
        
        current_round = memory.get_round_count()
        
        # Never accept over budget
        if seller_offer > self.budget:
            return False
            
        # Always accept if seller offer is significantly below our target
        target_price = int(self.budget * (1 - self.min_savings_target))
        if seller_offer <= target_price:
            return True
            
        # Accept if final offer and within budget
        if observation.get("is_final_offer") and seller_offer <= self.budget:
            return True
            
        # Get increasingly desperate as rounds progress
        if current_round >= self.desperation_threshold:
            # Accept anything within budget in late rounds
            return seller_offer <= self.budget
            
        # For diplomatic agents, be more accepting of reasonable offers
        if personality.personality_type == "diplomatic":
            reasonable_threshold = self.budget * 0.95  # Accept within 5% of budget
            if seller_offer <= reasonable_threshold:
                return True
                
        return False

    def _calculate_counter_offer(
        self, 
        seller_offer: int, 
        last_buyer_offer: Optional[int], 
        personality: BuyerPersonalityComponent,
        current_round: int
    ) -> int:
        """Improved counter-offer calculation"""
        
        if last_buyer_offer is None:
            # Opening offer - be more strategic
            if personality.personality_type == "aggressive":
                counter = int(seller_offer * 0.65)  # Start low
            elif personality.personality_type == "diplomatic":
                counter = int(seller_offer * 0.82)  # Start reasonable
            else:  # analytical
                counter = int(seller_offer * 0.75)  # Start with calculated value
        else:
            # Progressive concession with urgency awareness
            gap = min(seller_offer, self.budget) - last_buyer_offer
            
            # Base concession rate
            base_concession = gap * personality.concession_rate
            
            # Increase concession rate as deadline approaches
            urgency_multiplier = 1 + (current_round / self.max_rounds)
            concession = int(base_concession * urgency_multiplier)
            
            # Ensure minimum meaningful steps
            concession = max(2000, concession)  # Minimum ₹2000 steps
            
            counter = last_buyer_offer + concession
        
        # Ensure we stay within budget with safety margin
        safety_margin = max(2000, int(self.budget * 0.03))  # 3% safety margin
        max_offer = self.budget - safety_margin
        
        return max(5000, min(counter, max_offer))  # Minimum ₹5000 offer
    
# 4. Enhanced message generation with better personality traits
import random

def generate_personality_message(base_message: str, personality_type: str, context: str = "normal") -> str:
    phrases = {
        "aggressive": {
            "pressure": [
                "Let's cut the chase.",
                "Don’t waste my time.",
                "We both know that's overpriced."
            ],
            "final": [
                "This is my last offer.",
                "Take it or leave it.",
                "No more discussion after this."
            ]
        },
        "diplomatic": {
            "rapport": [
                "I value this conversation.",
                "Thanks for working with me.",
                "I respect your position."
            ],
            "collaboration": [
                "Let’s meet in the middle.",
                "We can find common ground.",
                "I think there’s room for compromise."
            ]
        },
        "analytical": {
            "data": [
                "Market trends suggest",
                "Based on my calculations,",
                "Looking at the data,"
            ],
            "logic": [
                "Economically speaking,",
                "Logically, it makes sense that",
                "From a numbers standpoint,"
            ]
        }
    }

    if personality_type in phrases and context in phrases[personality_type]:
        phrase = random.choice(phrases[personality_type][context])
        return f"{phrase} {base_message}"
    
    return base_message
   
def print_summary(results):
    print("\n" + "="*70)
    print("📊 FINAL BUYER AGENT PERFORMANCE SUMMARY")
    print("="*70)
    print(f"{'Personality':<15} | {'Deals Closed':<13} | {'Total Savings':<15} | Result")
    print("-"*70)
    
    for personality, data in results.items():
        deals = data["deals"]
        savings = data["savings"]
        result = "✅ PASS" if deals >= 2 else "❌ FAIL"
        print(f"{personality:<15} | {deals:<13} | ₹{savings:<14,} | {result}")
    
    print("="*70 + "\n")




# 3. Add a proper main function for testing
def main():
    """Main function to run tests"""
    print("🤖 AI Negotiation Agent - Technical Interview Project")
    print("Testing Buyer Agent Implementation with Concordia Framework")
    print("=" * 70)
    
    # Run comprehensive tests
    test_scenarios()
    
    print("\n" + "=" * 70)
    print("Testing completed. Review results above.")
    print("For interview submission, ensure 2+ successful deals per personality.")

if __name__ == "__main__":
    main()

