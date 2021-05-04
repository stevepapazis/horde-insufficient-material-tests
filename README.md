**TL;DR:** This script generates Horde positions and assesses whether white has enough material to deliver mate in each one of those positions. 

### The setting

[Horde](https://lichess.org/variant/horde) is a chess variant where the two opposing armies have different material compositions; black has the standard chess pieces while white only has pawns. Therefore white has to mate black in order to win and black needs to capture all of white's pawns/promoted-pieces. Those are the winning conditions for each side respectively.

When the time of one player is up, it is vital to know whether the other player has sufficient material to reach the winning condition in order to determine the outcome of the game. If the player with the remaining time on the clock has sufficient material to fulfill that condition, they are declared winner of the game, but if they don't have enough material the game is declared drawn.

On the one hand, black's winning condition can always get fulfilled as even a lone king can capture all the enemy pawns/pieces and win. On the other hand, white's winning chances depend on the material they're left with. For example, even a queen cannot deliver mate against a lone king when she is not supported by any other friendly piece.

When we say that white needs sufficient material to mate, we don't mean that there is a forced line in which white mates. What this actually means is that there exists a position after a sequence of moves that black is mated &mdash;perhaps with the worst possible, most illogical play by black.

Determining whether such a position exists and which order of moves needs to be played for that position to materialise can often be impractical. The next best try is to find all the positions where black is mated and check if white has enough material to recreate one of those positions, while assuming that that position can eventually be reached. Of course that assumption is not always true; there are some [clogged up](https://lichess.org/editor/1r3rk1/7p/p3b1pP/Pp1p1pP1/1PpPpP2/2P1P3/5B1B/2B5_w_-_-_0_1) positions where some square are inaccessible for each side.

### Finding positions where black is mated

The positions that black is mated can be divided in two categories:

1. positions where white has the necessary material to control all the squares around the enemy king (for example: two rooks against a lone king)
2. positions where white doesn't have the necessary material to control all the squares around the enemy king and relies on the fact that black has enough material to block off all the available escape routes of their king (for example: a knight that smothers a king in the corner)

The positions that belong to the first category are the ones where white has at least:

- [a queen + anything else](https://lichess.org/editor/k7/1Q6/2P5/8/8/8/8/8_b_-_-_0_1)
- [a pawn + anything else](https://lichess.org/editor/k7/1PP5/1PP5/8/8/8/8/8_b_-_-_0_1)
- a rook + a [rook](https://lichess.org/editor/8/8/8/8/8/8/3R4/k1R5_b_-_-_0_1)/[knight](https://lichess.org/editor/8/8/8/8/8/2N5/8/kR6_b_-_-_0_1)
- [a rook + the bishop pair](https://lichess.org/editor/8/8/8/8/8/1BB5/8/1k3R2_b_-_-_0_1)
- [a rook + two bishops on the same colour](https://lichess.org/editor/8/8/8/8/8/1B1B4/8/kR6_b_-_-_0_1)
- the bishop pair + a [knight](https://lichess.org/editor/8/8/8/8/8/1BB5/3N4/k7_b_-_-_0_1)/[bishop](https://lichess.org/editor/8/8/8/8/8/1BB5/2B5/k7_b_-_-_0_1)
- [three knights](https://lichess.org/editor/8/8/8/8/8/1NNN4/8/k7_b_-_-_0_1)
- [two knights + a bishop](https://lichess.org/editor/8/8/8/8/1N1B4/8/3N4/k7_b_-_-_0_1)
- [four or more pieces](https://lichess.org/editor/8/8/8/4B3/1N6/8/1B1N4/1k6_b_-_-_0_1) of which the bishops that occupy the same colour complex are no more than two<sup>[1](#myfootnote1)</sup>

Because of this fact, the positions of the second type are positions where white has at most:

- one piece
- two minor pieces
- a rook + a bishop
- a knight + two or more bishops on the same colour

From those four cases, the last two are the simplest to deal with; in both cases white can deliver mate if black has any piece other than the king. For example, if black has a knight, the bishop with the rook can mate the king like [this](https://lichess.org/editor/8/8/8/8/8/3B4/n7/kR6_b_-_-_0_1) and if black has a pawn/opposite-colour-bishop/rook/queen, he can get mated like [this](https://lichess.org/editor/8/8/8/8/8/2B5/2q5/Rk6_b_-_-_0_1). A knight + two bishops on the same colour can [control all the squares around the king](https://lichess.org/editor/8/8/8/8/8/B1N5/1B6/k7_b_-_-_0_1) but that position cannot be attained in a game without stalemating the king in the process. Therefore, if black were to get mated by the knight + two bishops, she needs to have at least an additional piece to waste a tempo.

Moreover, we can fairly easily handle some subcases of the first case.

- A lone queen can only mate the black king if black has at least a [pawn](https://lichess.org/editor/8/8/8/8/8/8/p7/k1Q5_b_-_-_0_1)/[rook](https://lichess.org/editor/8/8/8/8/8/8/r7/k1Q5_b_-_-_0_1) or [two bishops on the same colour](https://lichess.org/editor/8/8/8/8/8/2Q5/b7/kb6_b_-_-_0_1)
- A lone rook can only mate the black king if black can create a weak backrank or "[backfile](https://lichess.org/editor/kr6/1n6/R7/8/8/8/8/8_b_-_-_0_1)"; for example the king on A8 is mated by the rook if a pawn/rook is on A7 and a pawn/knight on B7<sup>[2](#myfootnote2)</sup>
- A lone pawn can mate the black king only in those cases where a lone knight/bishop/rook/queen can mate the king.

Hence, we're only left with positions to assess in which white has one or two minor pieces. To determine the mating patterns in those cases we can follow these steps:

- pick a square for the king and some combination of white pieces
- generate all the boards such as a white piece delivers check and the rest of the white pieces control some of the squares around the enemy king
- generate all the boards such as two white pieces deliver check in the form of a discovered attack and the rest of the white pieces control some of the squares around the enemy king
- for each one of these boards fill with black pieces the remaining squares around the king that white doesn't control so that the black king is mated

Because of symmetries we only need to place the king on A1, A2, A3 and A4.
Thus, we find that:

- a lone bishop can deliver mate only when black has at least [a pawn/opposite-colour-bishop + a pawn/opposite-colour-bishop](https://lichess.org/editor/8/8/8/8/8/2B5/p7/kb6_b_-_-_0_1).
- a lone knight can deliver mate only when black has at least [a knight/rook + a pawn/knight/bishop + one more piece](https://lichess.org/editor/8/8/8/8/8/8/qbN5/kr6_b_-_-_0_1) or a reordering of that material.
- two knights can deliver mate only when black has at least [a pawn/knight/bishop](https://lichess.org/editor/8/8/8/8/8/2N5/1nN5/k7_b_-_-_0_1).
- the bishop pair can deliver mate only when black has at least [a pawn/bishop](https://lichess.org/editor/8/8/8/8/8/2B5/b1B5/k7_b_-_-_0_1) or [a pawn/knight/bishop + a pawn/bishop/rook/queen](https://lichess.org/editor/8/8/8/qnB5/k7/8/2B5/8_b_-_-_0_1).
- two same-colour-bishops can deliver mate only when black has at least or [a pawn/knight/opposite-colour-bishop + a pawn/knight/opposite-colour-bishop](https://lichess.org/editor/8/8/8/8/8/8/bB6/knB5_b_-_-_0_1).
- a bishop + a knight can deliver mate only when black has at least [a pawn/opposite-colour-bishop](https://lichess.org/editor/8/8/8/8/8/2B5/b2N4/k7_b_-_-_0_1) or [two pieces](https://lichess.org/editor/8/8/8/4B3/8/1N6/q7/kq6_b_-_-_0_1).

### Aftermath

By having all these mating patterns we know the minimal sufficient material and we can assess any other position. When pawns are present, we also need to check if some of the pawns can be promoted to transform the position and meet the minimal sufficient material requirements.

---

Footnote:
<a name="myfootnote1"><sup>1</sup></a> : All the squares of a given colour around the king can be controlled by just two bishops that occupy the same colour.
<a name="myfootnote2"><sup>2</sup></a> : Positions with pawns have some really peculiar properties. For example, in a position where black possesses two split pawns against a lone rook, white cannot mate at first glance. But since the pawns can be promoted to a rook and a knight, the position is winnable regardless of the initial positioning of the pawns. Applying the same concept more generally, we see that the limited mobility of pawns doesn't always constitute an obstacle to the attainability of a position.
