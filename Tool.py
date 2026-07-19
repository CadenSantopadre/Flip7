card_num = []

BANK = {
    0: 1, 
    1: 1, 
    2: 2, 
    3: 3, 
    4: 4, 
    5: 5, 
    6: 6, 
    7: 7, 
    8: 8, 
    9: 9, 
    10: 10, 
    11: 11, 
    12: 12
}

def calculate_bust_probability(pulled_card_history):
    current_hand = set(pulled_card_history)
    
    current_deck = BANK.copy()
    for card in pulled_card_history:
        if card in current_deck and current_deck[card] > 0:
            current_deck[card] -= 1

    total_remaining_cards = sum(current_deck.values())
    if total_remaining_cards == 0:
        return 0.0

    matching_bust_cards = sum(current_deck[card] for card in current_hand if card in current_deck)
    
    return matching_bust_cards / total_remaining_cards

print("Type 'exit' to leave")
while True:
    choice = input("Enter the card pulled: ").strip()
    
    if choice.lower() == 'exit':
        break
        
    try:
        processed_input = int(choice)
        
        if processed_input not in BANK:
            print("Invalid card! Must be between 0 and 12.")
            continue
            
        current_count = BANK[processed_input] - card_num.count(processed_input)
        if current_count <= 0:
            print(f"Invalid card! All {BANK[processed_input]} copies have been drawn.")
            continue
            
        card_num.append(processed_input)
        
        final_bust_prob = calculate_bust_probability(card_num)
        
        print(f"Logged Card: {processed_input} | Current Hand: {card_num}\n")
        
    except ValueError:
        print("Invalid input. Please enter a valid integer card number.")

print("\n--- FINAL RESEARCH METRICS ---")
print(f"Total cards given: {len(card_num)}")
print(f"Bust probability:  {final_bust_prob * 100:.2f}%")