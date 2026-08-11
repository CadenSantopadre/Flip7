import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QRadioButton, QButtonGroup, QTextEdit, QFrame,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Build the starting deck as a dictionary mapping each card to how many
# copies of it exist. Numbers are stored as ints, everything else as
# strings, so we can tell them apart later with isinstance checks.
FULL_DECK = {}
for n in range(13):
    FULL_DECK[n] = 1 if n in (0, 1) else n
for mod in ["+2", "+4", "+6", "+8", "+10", "x2"]:
    FULL_DECK[mod] = 1
for action in ["Freeze", "Flip Three", "Second Chance"]:
    FULL_DECK[action] = 3

NUMBER_CARDS = list(range(13))
MODIFIER_CARDS = ["+2", "+4", "+6", "+8", "+10", "x2"]
ACTION_CARDS = ["Freeze", "Flip Three", "Second Chance"]

TOTAL_DECK_SIZE = sum(FULL_DECK.values())
TOTAL_NUMBER_CARDS = sum(FULL_DECK[n] for n in NUMBER_CARDS)


class Flip7Tracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flip 7 Bust Probability Tracker")
        self.resize(760, 820)

        # remaining tracks how many of each card are still unseen in the deck
        self.remaining = dict(FULL_DECK)
        # my_row is the set of numbers currently sitting in front of you
        self.my_row = set()
        self.my_second_chance = False
        # history holds past states so the undo button has something to pop
        self.history = []

        self.card_buttons = {}

        self._build_ui()
        self._update_display()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)

        # top panel with the big probability number and a few quick stats
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.Shape.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)

        self.prob_label = QLabel("0.0%")
        self.prob_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prob_label.setFont(QFont("Arial", 42, QFont.Weight.Bold))
        stats_layout.addWidget(self.prob_label)

        self.prob_sub_label = QLabel("Bust probability on your next number card")
        self.prob_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.prob_sub_label)

        detail_row = QHBoxLayout()
        self.deck_label = QLabel("Deck remaining: 94")
        self.row_label = QLabel("My row: (empty)")
        self.sc_label = QLabel("Second Chance: No")
        for lbl in (self.deck_label, self.row_label, self.sc_label):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            detail_row.addWidget(lbl)
        stats_layout.addLayout(detail_row)

        root.addWidget(stats_frame)

        # lets you say who a click applies to before you press a card button
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Card drawn for:"))
        self.me_radio = QRadioButton("Me")
        self.opp_radio = QRadioButton("Opponent")
        self.me_radio.setChecked(True)
        self.target_group = QButtonGroup(self)
        self.target_group.addButton(self.me_radio)
        self.target_group.addButton(self.opp_radio)
        target_row.addWidget(self.me_radio)
        target_row.addWidget(self.opp_radio)
        target_row.addStretch()
        root.addLayout(target_row)

        # number buttons are the ones that actually matter for bust math
        root.addWidget(self._section_label("Number Cards"))
        num_grid = QGridLayout()
        cols = 7
        for i, n in enumerate(NUMBER_CARDS):
            btn = QPushButton()
            btn.setMinimumHeight(56)
            btn.clicked.connect(lambda _, c=n: self._record_card(c))
            num_grid.addWidget(btn, i // cols, i % cols)
            self.card_buttons[n] = btn
        root.addLayout(num_grid)

        # modifiers and actions still need to be tracked so the deck count
        # stays honest, they just don't feed into the bust percentage
        root.addWidget(self._section_label("Modifiers"))
        mod_row = QHBoxLayout()
        for m in MODIFIER_CARDS:
            btn = QPushButton()
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda _, c=m: self._record_card(c))
            mod_row.addWidget(btn)
            self.card_buttons[m] = btn
        root.addLayout(mod_row)

        root.addWidget(self._section_label("Action Cards"))
        act_row = QHBoxLayout()
        for a in ACTION_CARDS:
            btn = QPushButton()
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda _, c=a: self._record_card(c))
            act_row.addWidget(btn)
            self.card_buttons[a] = btn
        root.addLayout(act_row)

        root.addWidget(self._section_label("Log"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        root.addWidget(self.log)

        ctrl_row = QHBoxLayout()
        undo_btn = QPushButton("Undo Last")
        undo_btn.clicked.connect(self._undo)
        new_round_btn = QPushButton("New Round (keep deck)")
        new_round_btn.clicked.connect(self._new_round)
        reset_btn = QPushButton("New Game (reset deck)")
        reset_btn.clicked.connect(self._reset_deck)
        for b in (undo_btn, new_round_btn, reset_btn):
            b.setMinimumHeight(40)
            ctrl_row.addWidget(b)
        root.addLayout(ctrl_row)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        return lbl

    def _snapshot(self):
        # called right before any state change so undo has a state to
        # restore, we cap the history so it doesn't grow forever in a
        # long play session
        self.history.append((dict(self.remaining), set(self.my_row), self.my_second_chance))
        if len(self.history) > 100:
            self.history.pop(0)

    def _undo(self):
        if not self.history:
            return
        self.remaining, self.my_row, self.my_second_chance = self.history.pop()
        self._append_log("<i>Undo last action.</i>")
        self._update_display()

    def _record_card(self, card):
        if self.remaining.get(card, 0) <= 0:
            QMessageBox.warning(self, "No cards left",
                                 f"There are no more '{card}' cards left in the deck.")
            return

        target = "me" if self.me_radio.isChecked() else "opponent"
        self._snapshot()
        self.remaining[card] -= 1

        label = str(card)
        who = "You" if target == "me" else "Opponent"
        line = f"{who} drew <b>{label}</b>."

        if target == "me":
            if isinstance(card, int):
                if card in self.my_row:
                    # you already have this number, so this is a bust
                    # unless a second chance is sitting there to eat it
                    if self.my_second_chance:
                        self.my_second_chance = False
                        line += " <span style='color:#f39c12'>Duplicate! Bust avoided via Second Chance.</span>"
                    else:
                        line += " <span style='color:#e74c3c'><b>BUST!</b> Row cleared.</span>"
                        self.my_row.clear()
                else:
                    self.my_row.add(card)
            elif card == "Second Chance":
                self.my_second_chance = True
                line += " You now hold a Second Chance."
            elif card == "Freeze":
                line += " You froze this round."
            elif card == "Flip Three":
                line += " Draw 3 more cards now, click each one as it appears."

        self._append_log(line)
        self._update_display()

    def _append_log(self, html_line):
        self.log.append(html_line)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _new_round(self):
        # clears your row for the next hand but leaves the deck counts
        # alone, since the same deck usually carries over between rounds
        self._snapshot()
        self.my_row.clear()
        self.my_second_chance = False
        self._append_log("<i>New round started, deck unchanged.</i>")
        self._update_display()

    def _reset_deck(self):
        reply = QMessageBox.question(
            self, "New Game",
            "Reset the entire deck and clear all tracked state?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.remaining = dict(FULL_DECK)
        self.my_row.clear()
        self.my_second_chance = False
        self.history.clear()
        self.log.clear()
        self._append_log("<i>New game, deck reset to 94 cards.</i>")
        self._update_display()

    def _update_display(self):
        # total cards left in the whole deck, just for the info line
        total_remaining = sum(self.remaining.values())

        # bust math only cares about number cards, since modifiers and
        # action cards can never cause a bust when drawn
        number_cards_remaining = sum(self.remaining[n] for n in NUMBER_CARDS)
        dangerous = sum(self.remaining.get(n, 0) for n in self.my_row)

        if number_cards_remaining > 0:
            prob = dangerous / number_cards_remaining
        else:
            prob = 0.0
        pct = prob * 100

        self.prob_label.setText(f"{pct:.1f}%")
        if pct < 15:
            color = "#2ecc71"
        elif pct < 35:
            color = "#f39c12"
        else:
            color = "#e74c3c"
        self.prob_label.setStyleSheet(f"color: {color};")

        self.prob_sub_label.setText(
            f"{dangerous} dangerous number(s) out of {number_cards_remaining} number cards remaining"
        )
        self.deck_label.setText(f"Deck remaining: {total_remaining}/{TOTAL_DECK_SIZE}")
        row_text = ", ".join(str(x) for x in sorted(self.my_row)) if self.my_row else "(empty)"
        self.row_label.setText(f"My row: {row_text}")
        self.sc_label.setText(f"Second Chance: {'Yes' if self.my_second_chance else 'No'}")
        self.sc_label.setStyleSheet(
            "color: #2ecc71; font-weight: bold;" if self.my_second_chance else ""
        )

        # walk every button and refresh its label, enabled state, and
        # highlight so the board always matches the current state
        for card, btn in self.card_buttons.items():
            left = self.remaining.get(card, 0)
            label = str(card)
            is_mine = isinstance(card, int) and card in self.my_row
            btn.setText(f"{label}\n({left} left)")
            btn.setEnabled(left > 0)
            if is_mine:
                btn.setStyleSheet(
                    "background-color: #fdebd0; font-weight: bold; border: 2px solid #f39c12;"
                )
            else:
                btn.setStyleSheet("")


def main():
    app = QApplication(sys.argv)
    window = Flip7Tracker()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()