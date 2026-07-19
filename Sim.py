import random
import csv
import os
from collections import defaultdict

BANK = { #There's 1 Zero, 1 One, 2 Twos...
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
    12: 12,
    "f3": 3, #Flip 3
    "fr": 3, #Freeze
    "sec": 3, #Second Chance
    "2+": 1, 
    "4+": 1, 
    "6+": 1, 
    "8+": 1, 
    "10+": 1,
    "2x": 1,
}

MOD_VALUES = {"2+": 2, "4+": 4, "6+": 6, "8+": 8, "10+": 10} #Converting 2+ into 2

CUSTOM_THRESHOLDS = [
    0.00,
    0.10,
    0.20,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
    1.00
]
FIXED_THRESHOLD = 0.45 #"Human" threshold, found through repeated analysis of multiple sets
GAMES_TO_SIMULATE = 50_000 #Customize to whatever, but your memory is going to need to handle it
OUTPUT_DIR = "."


class Deck:
    def __init__(self):
        self.cards = [card for card, count in BANK.items() for _ in range(count)] #"card" (output) for "item" (card), count in BANK.items()
        random.shuffle(self.cards)

    def draw_card(self):
        if not self.cards: #If there are no cards left, return None
            return None
        return self.cards.pop() #return a card and remove it with .pop()

    def bust_probability(self, player):
        if not self.cards:
            return 0.0 #If no cards, perfectly safe I guess
        held = set(player.hand)
        if not held:
            return 0.0 #If first turn, perfectly safe
        matching = sum(1 for c in self.cards if isinstance(c, int) and c in held) #Add 1 matching card for each card that matches
        return matching / len(self.cards) #Then divide by total cards in deck
    
    def get_avg_value(self): #This is for calculating EV
        numeric_cards = [c for c in self.cards if isinstance(c, int)]
        
        if not numeric_cards:
            return 0.0
            
        return sum(numeric_cards) / len(numeric_cards)


class Player:
    def __init__(self, name, threshold):
        self.name = name
        self.threshold = threshold

        self.hand = []
        self.has_second_chance = False
        self.has_x2 = False
        self.mod_flat = 0 #Mod flat is the modifiers... +2, +4

        self.active = True
        self.busted = False
        self.flip7 = False
        self.score = 0
        self.draws_this_round = 0
        self.second_chances_used = 0

    def reset_round(self):
        self.hand = []
        self.has_second_chance = False
        self.has_x2 = False
        self.mod_flat = 0 
        self.active = True
        self.busted = False
        self.flip7 = False
        self.score = 0
        self.draws_this_round = 0
        self.second_chances_used = 0

    def get_threshold(self, round_number):
        if callable(self.threshold): #If in a round, give the bust rate
            return self.threshold(self, round_number)
        return self.threshold

    def running_value(self):
        number_total = sum(self.hand) * (2 if self.has_x2 else 1) #Running value is the sum of cards' values
        return number_total + self.mod_flat #Plus the +2 and +4s
    
    def expected_value(self, deck):
        bust_prob = deck.bust_probability(self)
        avg_card = deck.get_avg_value()

        survive_value = self.running_value() + avg_card

        ev = ((1 - bust_prob) * (survive_value)) - ((bust_prob) * self.running_value())
        #ev = P(Win) * survive_value - P(Bust)*Running_Value
        return ev

    def finalize_score(self, bonus=0):
        self.score = self.running_value() + bonus


def pick_random_other_active(players, caster): #This is for applying f3 and fr
    others = [p for p in players if p is not caster and p.active]
    if not others:
        return caster #You must choose yourself if there is nobody else.
    return random.choice(others)


class StatsCollector:
    def __init__(self):
        self.draw_records = [] #We keep a record of the draws to make sure we are statistically sound
        self.round_records = [] #We keep a record of the roudns to see how long they last and such
        self._draw_index_by_round_player = defaultdict(list)

    def log_draw(self, round_id, player, card, busted_this_draw, is_forced, deck):
        self.draw_records.append({ #Keep track of and append these things...
            "round_id": round_id,
            "player": player.name, 
            "draw_number": player.draws_this_round,
            "card": card,
            "busted_this_draw": busted_this_draw,
            "running_number_total": sum(player.hand),
            "running_value": player.expected_value(deck),
            "expected_value": player.expected_value(deck),
            "has_second_chance": player.has_second_chance,
            "has_x2": player.has_x2,
            "is_forced": is_forced,
            "round_won": None, #This is inputted later
            "round_final_score": None,
        })
        self._draw_index_by_round_player[(round_id, player.name)].append(len(self.draw_records) - 1)

    def finalize_round(self, round_id, players):
        best_score = max(p.score for p in players) #best score is the max of all the scores

        for player in players:
            won = player.score == best_score #The won truth value is if their score == best
            self.round_records.append({
                "round_id": round_id,
                "player": player.name,
                "threshold": player.threshold if not callable(player.threshold) else "custom_fn",
                "final_score": player.score,
                "busted": player.busted,
                "flip7": player.flip7,
                "total_draws": player.draws_this_round,
                "second_chances_used": player.second_chances_used,
                "unique_numbers_held": len(player.hand),
                "won": won,
            })

            for idx in self._draw_index_by_round_player.get((round_id, player.name), []): #Every time we append (above), let round_won be the truth value we got from earlier
                self.draw_records[idx]["round_won"] = won
                self.draw_records[idx]["round_final_score"] = player.score

    def write_lag_k_bust_probability(self, path):
        attempts = defaultdict(int) #defaultdict makes a __missing__() method when you call soemthing that doesn't exist... 
        busts = defaultdict(int) #Then it creates something for it
                                 #DefualtDict is better becuase we're making ["draw_number" : 10, "busted" : True] and stuff like that
        for r in self.draw_records:
            k = r["draw_number"] #We're looking at change per round, so we have 'k' rounds
            attempts[k] += 1
            if r["busted_this_draw"]:
                busts[k] += 1

        with open(path, "w", newline="") as f: #We then write a csv for it
            writer = csv.writer(f)
            writer.writerow(["draw_number_k", "attempts", "busts", "bust_rate"])
            for k in sorted(attempts):
                rate = busts[k] / attempts[k] if attempts[k] else 0.0
                writer.writerow([k, attempts[k], busts[k], round(rate, 6)])

    def write_lag_k_expected_value(self, path):
        totals = defaultdict(float)
        counts = defaultdict(int)
        sumsq = defaultdict(float)
        for r in self.draw_records:
            k = r["draw_number"]
            v = r["expected_value"]
            totals[k] += v
            sumsq[k] += v * v #We need the sumsq for stdev calculations
            counts[k] += 1

        means = {}
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["draw_number_k", "samples", "mean_expected_value", "std_expected_value", "marginal_gain_vs_prev_k"])
            for k in sorted(counts):
                mean = totals[k] / counts[k]
                var = sumsq[k] / counts[k] - mean ** 2 #variance calculation
                std = var ** 0.5 if var > 0 else 0.0 #stdev calculation
                means[k] = mean
                prev_mean = means.get(k - 1)
                marginal = mean - prev_mean if prev_mean is not None else "" #marginal is like the derivative
                writer.writerow([k, counts[k], round(mean, 4), round(std, 4), marginal])

    def write_round_length_distribution(self, path):
        lengths = defaultdict(int)
        for r in self.round_records:
            lengths[r["total_draws"]] += 1
        total = sum(lengths.values())

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["round_length_draws", "count", "proportion"])
            for length in sorted(lengths):
                writer.writerow([length, lengths[length], round(lengths[length] / total, 6)])

    def write_card_draw_frequency(self, path):
        counts = defaultdict(int)
        for r in self.draw_records:
            counts[r["card"]] += 1
        total = sum(counts.values())

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["card", "count", "proportion"])
            for card in sorted(counts, key=lambda c: str(c)):
                writer.writerow([card, counts[card], round(counts[card] / total, 6)])

    def write_bust_cause_breakdown(self, path):
        counts = defaultdict(int)
        for r in self.draw_records:
            if r["busted_this_draw"]:
                counts[r["card"]] += 1
        total = sum(counts.values())

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["duplicate_number", "bust_count", "proportion_of_busts"])
            for card in sorted(counts):
                prop = counts[card] / total if total else 0.0
                writer.writerow([card, counts[card], round(prop, 6)])

    def write_final_score_summary(self, path):
        by_player = defaultdict(list)
        for r in self.round_records:
            by_player[r["player"]].append(r)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["player", "threshold", "games", "mean_score", "std_score", "median_score", "win_rate", "bust_rate", "flip7_rate", "avg_draws_per_round", "avg_second_chances_used"])
            for player_name, rows in by_player.items():
                scores = sorted(r["final_score"] for r in rows)
                n = len(scores)
                mean = sum(scores) / n
                var = sum((s - mean) ** 2 for s in scores) / n
                std = var ** 0.5
                median = scores[n // 2] if n % 2 else (scores[n // 2 - 1] + scores[n // 2]) / 2
                bust_rate = sum(1 for r in rows if r["busted"]) / n
                flip7_rate = sum(1 for r in rows if r["flip7"]) / n
                avg_draws = sum(r["total_draws"] for r in rows) / n
                avg_sc = sum(r["second_chances_used"] for r in rows) / n
                win_rate = sum(1 for r in rows if r["won"]) / n

                writer.writerow([player_name, rows[0]["threshold"], n, round(mean, 4),
                                  round(std, 4), median, round(win_rate, 6), round(bust_rate, 6),
                                  round(flip7_rate, 6), round(avg_draws, 4), round(avg_sc, 4)])

    def write_custom_lag_k_performance(self, path, player_name="Custom"):
        rows = [r for r in self.draw_records if r["player"] == player_name]

        by_k = defaultdict(list)
        for r in rows:
            by_k[r["draw_number"]].append(r)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["draw_number_k", "samples", "win_rate", "mean_running_value", "std_running_value", "bust_rate_at_k"])
            for k in sorted(by_k):
                group = by_k[k]
                n = len(group)
                win_rate = sum(1 for r in group if r["round_won"]) / n
                values = [r["running_value"] for r in group]
                mean_v = sum(values) / n
                var_v = sum((v - mean_v) ** 2 for v in values) / n
                std_v = var_v ** 0.5
                bust_rate = sum(1 for r in group if r["busted_this_draw"]) / n
                writer.writerow([k, n, round(win_rate, 6), round(mean_v, 4),
                                  round(std_v, 4), round(bust_rate, 6)])

    def write_custom_final_stop_summary(self, path, player_name="Custom"):
        rows = [r for r in self.round_records if r["player"] == player_name]

        by_len = defaultdict(list)
        for r in rows:
            by_len[r["total_draws"]].append(r)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["total_draws", "samples", "win_rate", "mean_score", "std_score", "bust_rate", "flip7_rate"])
            for length in sorted(by_len):
                group = by_len[length]
                n = len(group)
                win_rate = sum(1 for r in group if r["won"]) / n
                scores = [r["final_score"] for r in group]
                mean_s = sum(scores) / n
                var_s = sum((s - mean_s) ** 2 for s in scores) / n
                std_s = var_s ** 0.5
                bust_rate = sum(1 for r in group if r["busted"]) / n
                flip7_rate = sum(1 for r in group if r["flip7"]) / n
                writer.writerow([length, n, round(win_rate, 6), round(mean_s, 4),
                                  round(std_s, 4), round(bust_rate, 6), round(flip7_rate, 6)])

    def write_all(self, output_dir=".", tracked_player="Custom"): #This creates the files with the csv data we wrote
        self.write_lag_k_bust_probability(f"{output_dir}/lag_k_bust_probability.csv")
        self.write_lag_k_expected_value(f"{output_dir}/lag_k_expected_value.csv")
        self.write_round_length_distribution(f"{output_dir}/round_length_distribution.csv")
        self.write_card_draw_frequency(f"{output_dir}/card_draw_frequency.csv")
        self.write_bust_cause_breakdown(f"{output_dir}/bust_cause_breakdown.csv")
        self.write_final_score_summary(f"{output_dir}/final_score_summary.csv")
        self.write_custom_lag_k_performance(f"{output_dir}/custom_lag_k_performance.csv", tracked_player)
        self.write_custom_final_stop_summary(f"{output_dir}/custom_final_stop_summary.csv", tracked_player)


def draw_and_resolve(player, players, deck, round_id, stats, is_forced=False): #This is how we set up the drawing process
    if not player.active or not deck.cards:
        return

    card = deck.draw_card()
    if card is None:
        return

    player.draws_this_round += 1
    busted_this_draw = False

    if isinstance(card, int): #If draw number(int) card, then check second chance and add to pile
        if card in player.hand:
            if player.has_second_chance:
                player.has_second_chance = False
                player.second_chances_used += 1
            else:
                player.busted = True
                player.active = False
                player.score = 0
                busted_this_draw = True
        else:
            player.hand.append(card)
            if len(player.hand) == 7:
                player.flip7 = True
                player.active = False
                player.finalize_score(bonus=15)

    elif card == "f3": #If flip 3, pick randomly and give 3
        stats.log_draw(round_id, player, card, busted_this_draw, is_forced, deck)
        target = pick_random_other_active(players, player)
        if target is None: #If nobody else, has to do himself
            target = player
        for _ in range(3):
            if not target.active or not deck.cards:
                break
            draw_and_resolve(target, players, deck, round_id, stats, is_forced=True)
        return

    elif card == "fr": #If freeze, pick and freeze
        stats.log_draw(round_id, player, card, busted_this_draw, is_forced, deck)
        target = pick_random_other_active(players, player)
        if target is None:
            target = player
        if target.active:
            target.finalize_score()
            target.active = False
        return

    elif card == "sec":
        if not player.has_second_chance:
            player.has_second_chance = True

    elif card in MOD_VALUES:
        player.mod_flat += MOD_VALUES[card]

    elif card == "2x":
        player.has_x2 = True

    stats.log_draw(round_id, player, card, busted_this_draw, is_forced, deck)


def play_round(players, round_id, stats, round_number=0):
    for p in players:
        p.reset_round()

    deck = Deck()

    while any(p.active for p in players) and deck.cards:
        for player in players:
            if not player.active:
                continue
            if not deck.cards:
                break

            prob = deck.bust_probability(player)
            threshold = player.get_threshold(round_number)

            if prob > threshold:
                player.finalize_score()
                player.active = False
                continue

            draw_and_resolve(player, players, deck, round_id, stats, is_forced=False)

    for player in players:
        if player.active:
            player.finalize_score()
            player.active = False

    stats.finalize_round(round_id, players)

    return deck


def make_bots(custom_threshold, fixed_threshold):
    return [
        Player("Bot A", fixed_threshold),
        Player("Bot B", fixed_threshold+5),
        Player("Bot C", fixed_threshold-5),
        Player("Custom", custom_threshold),
    ]


def run_study(custom_threshold, games_to_simulate, fixed_threshold):
    players = make_bots(custom_threshold, fixed_threshold)
    stats = StatsCollector()

    for round_id in range(games_to_simulate):
        play_round(players, round_id, stats, round_number=round_id)

    return stats


if __name__ == "__main__":

    for threshold in CUSTOM_THRESHOLDS:
        print(f"Running threshold {threshold:.2f}")

        stats = run_study(
            custom_threshold=threshold,
            games_to_simulate=GAMES_TO_SIMULATE,
            fixed_threshold=FIXED_THRESHOLD,
        )

        folder = os.path.join(
            OUTPUT_DIR,
            f"threshold_{threshold:.2f}"
        )

        os.makedirs(folder, exist_ok=True)
        stats.write_all(folder)