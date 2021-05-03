from chess import Board, Move, Piece, SquareSet
from chess import BB_BACKRANKS, BB_DARK_SQUARES, BB_LIGHT_SQUARES
from chess import ( A1, A2, A3, A4, A5, A6, A7, A8,
                    B1, B2, B3, B4, B5, B6, B7, B8,
                    C1, C2, C3, C4, C5, C6, C7, C8,
                    D1, D2, D3, D4, D5, D6, D7, D8,
                    E1, E2, E3, E4, E5, E6, E7, E8,
                    F1, F2, F3, F4, F5, F6, F7, F8,
                    G1, G2, G3, G4, G5, G6, G7, G8,
                    H1, H2, H3, H4, H5, H6, H7, H8 )
from chess import popcount, square, square_name, square_file, square_rank

from copy import deepcopy
from os.path import abspath
from time import time


class WrappedBoard(Board):
    def __init__(self, fen="8/8/8/8/8/8/8/8 b - - 0 1", name="", is_insufficient=True):
        super().__init__(fen)
        self.comment = name
        self.is_insufficient = is_insufficient

    @staticmethod
    def mirror_square(square):
        from chess import square as sq
        return sq(7-square_file(square), square_rank(square))

    @staticmethod
    def is_backrank(square):
        return (square in range(0,8)) or (square in range(56,64))

    def get_empty_square(self):
        """Gets an empty square not in the backranks."""
        return SquareSet(72057594037927680).difference(self.occupied).pop()

    def mirror_vertical(self):
        mirrored = WrappedBoard('8/8/8/8/8/8/8/8 b - - 0 1', self.comment, self.is_insufficient)
        for i in range(8):
            for j in range(8):
                sq = square(i,j)
                piece = self.piece_at(sq)
                if piece:
                    mirrored.set_piece_at(self.mirror_square(sq), piece)
        mirrored.compute_white_composition()
        mirrored.compute_black_composition()
        return mirrored

    def compute_white_composition(self):
        """
        Returns the material composition of the white side.

        Only up to two same colour bishops are taken into account.
        """
        white = self.occupied_co[1]
        dark = popcount(white&self.bishops&BB_DARK_SQUARES)
        dark = 2 if dark>=2 else dark
        light = popcount(white&self.bishops&BB_LIGHT_SQUARES)
        light = 2 if light>=2 else light

        self.white_composition = (
            popcount(white&self.pawns),
            dark+light,
            popcount(white&self.knights),
            popcount(white&self.rooks),
            popcount(white&self.queens),
            dark,
            light
            )

        return self.white_composition

    def compute_black_composition(self):
        black = self.occupied_co[0]
        self.black_composition = (
            popcount(black&self.pawns),
            popcount(black&self.bishops),
            popcount(black&self.knights),
            popcount(black&self.rooks),
            popcount(black&self.queens),
            popcount(black&self.bishops&BB_DARK_SQUARES),
            popcount(black&self.bishops&BB_LIGHT_SQUARES)
            )
        return self.black_composition

    def __le__(self, other):
        """Is the material on 'self' a subset of the material on 'other'?"""
        for i in range(7):
            if self.white_composition[i] > other.white_composition[i]:
                return False
        for i in range(7):
            if self.black_composition[i] > other.black_composition[i]:
                return False
        return True

    def __ge__(self, other):
        """Is the material on 'self' a superset of the material on 'other'?"""
        return other <= self

    def deepcopy(self):
        return WrappedBoard(self.fen(), self.comment, self.is_insufficient)

    def print(self):
        print( "\n".join([self.comment,self.__str__(),self.fen(),str(self.is_insufficient)])+"\n" )



class MaterialCompositions:
    def __init__(self):
        """A dictionary to keep the material compositions."""
        self.material = dict()
        self.boards = dict()

    @staticmethod
    def __is_tuple1_subset_tuple2(tuple1, tuple2):
        if tuple1[0] > tuple2[0]:
            return False
        for j in range(2,7):
            if tuple1[j] > tuple2[j]:
                return False
        return True

    @staticmethod
    def __mirror(tuple):
        return tuple[0],tuple[1],tuple[2],tuple[3],tuple[4],tuple[6],tuple[5]
    

    def add(self, board):
        """
        Adds a board in the collection.
        If the board has bishops then its vertical mirroring is also added.
        """
        white_comp = board.white_composition
        self.material.setdefault(white_comp,set())

        black_comp = board.black_composition

        for cand_black_comp in self.material[white_comp]:
            if self.__is_tuple1_subset_tuple2(cand_black_comp,black_comp):
                return None
        else:
            self.material[white_comp].add(black_comp)
            self.boards.setdefault( white_comp, dict() )[black_comp] = board

            if board.bishops:
                self.material.setdefault( self.__mirror(white_comp), set() ).add( self.__mirror(black_comp) )
                self.boards.setdefault( self.__mirror(white_comp), dict() )[self.__mirror(black_comp)] = board.mirror_vertical()


    def  __len__(self):
        return sum( [ 1 for i in self.material for j in self.material[i]] )

    def __getitem__(self, i):
        return self.material[i]

    def exists_subset_of(self, board):
        """
        Returns True if the material composition of 'board' has a subset
        material composition in 'self' or if there are enough black pawns
        that can be promoted to reach such a state.
        """
        try:
            if board.sufficient_subset:
                return True
        except AttributeError:
            pass

        for white_comp in self.material:
            if self.__is_tuple1_subset_tuple2(white_comp, board.white_composition):

                if board.black_composition in self.material[white_comp]:
                    board.sufficient_subset = (white_comp,board.black_composition)
                    return True

                for black_comp in self.material[white_comp]:
                    if black_comp[0] > board.black_composition[0]:
                        continue
                    residual_pawns =  board.black_composition[0] - black_comp[0]
                    for j in range(2,7):
                        if black_comp[j] > board.black_composition[j]:
                            residual_pawns += board.black_composition[j] - black_comp[j]
                            if residual_pawns < 0:
                                break
                    else:
                        board.sufficient_subset = (white_comp,black_comp)
                        self.boards.setdefault(board.white_composition,dict())[board.black_composition] = self.boards[white_comp][black_comp]
                        return True

        board.sufficient_subset = None
        return False



class GenerateTestsFromPatterns:
    def __init__(self):
        """Use add_pattern to add patterns."""
        self.tests = dict()
        self.minimal_sufficient_material = MaterialCompositions()
        self.FENs = set()
        self.BB_BORDER = SquareSet(18411139144890810879)
        self.BB_BACKRANKS = SquareSet(BB_BACKRANKS)
        self.BB_DARK_SQUARES = SquareSet(BB_DARK_SQUARES)
        self.BB_LIGHT_SQUARES = SquareSet(BB_LIGHT_SQUARES)

    def __add(self, board):
        if board.fen() in self.FENs:
            return None
        board.compute_white_composition()
        board.compute_black_composition()
        board.has_sufficient_subset = lambda : self.minimal_sufficient_material.exists_subset_of(board)
        if board.is_insufficient and board.has_sufficient_subset():
            board.is_insufficient = False
        if board.is_insufficient == False:
            self.minimal_sufficient_material.add( board )
        self.tests.setdefault(board.comment,[]).append( board )
        self.FENs.add( board.fen() )
        if board.bishops:
            self.__add( board.mirror_vertical() )

    def has_sufficient_subset(self, board):
        return self.minimal_sufficient_material.exists_subset_of(board)

    def add_pattern(self, name, black_pattern, black_king_square=A1, white=[], is_insufficient=False, generate_insufficient=True, dont_spam=False):
        """
        Creates tests for a given black pattern.

        For the pattern (A2,"bp"),(B3,"bq") we get four cases:
        - (A2,"b"),(B3,"b")
        - (A2,"b"),(B3,"q")
        - (A2,"p"),(B3,"b")
        - (A2,"p"),(B3,"q")

        name: The name of the pattern.
              e.g. "black king, queen and knight against white bishops and queen"
              If the name already exists, it appends the new test cases.

        black_pattern: A list of (square, string).
                       Each string contains the symbols of the black pieces that
                       can occupy that square.
                       The king should not be included.
                       e.g. [(H7,"pq"),(D4,"pbnrq"),(E4,"bn")]

        black_king_square: The square occupied by the black king.

        white: A list of (square,white_piece_symbol) indicating where the white army is.
               e.g. [(A2,"P"),(A3,"Q")]

        is_insufficient: Does the given input represent a position in which white can mate?
                         Ideally, if is_insufficient==False, the provided position should
                         showcase that possibility.

        generate_insufficient: Produce tests for the case 'not is_insufficient' when
                               'is_insufficient==False'.
                               e.g. If black_pattern=[(A2,"bnq")], then create tests
                               for the cases where black_pattern=[(A2,"pr")]

        There is no validation for the data provided by the caller.
        """

        black_squares = [i[0] for i in black_pattern]

        base_board = WrappedBoard("8/8/8/8/8/8/8/8 b - - 0 1", name, is_insufficient)
        for square,piece in white:
            base_board.set_piece_at( square, Piece.from_symbol(piece) )
        base_board.set_piece_at( black_king_square, Piece.from_symbol("k") )

        self.tests.setdefault(name,[])

        self.add_boards_from(
            name,
            black_pattern,
            is_insufficient,
            base_board
            )

        if generate_insufficient and is_insufficient == False:
            for anti_pattern in self.__anticombinations(black_pattern):
                self.add_boards_from(
                    name,
                    [(sq,anti_pattern[n]) for n,sq in enumerate(black_squares)],
                    not is_insufficient,
                    base_board
                    )

        if False:#not dont_spam:
            for board in self.tests[name]:
                if board.is_checkmate()==board.is_insufficient:
                    print("In '",name,"' there exists a board such as\
                          \nboard.is_checkmate() == ",board.is_checkmate()," == board.is_insufficient",sep="")
                    board.print()


    def add_single_test(self, name, fen,  is_insufficient=False):
        board = WrappedBoard(fen,name,is_insufficient)
        self.__add( board )

    def add_tests_from_white_pattern(self, name, white_pattern, black_king_square=A1, is_insufficient=False):
        """Creates tests when a white pattern=[(sq,"pieces"),...] is given."""
        white_combinations = self.__compute_combinations([piece for sq,piece in white_pattern])
        for white_side in white_combinations:
            board = WrappedBoard()
            board.set_piece_at(black_king_square,Piece.from_symbol("k"))
            for white_piece in white_side:
                sq = board.get_empty_square()
                board.set_piece_at(sq,Piece.from_symbol(white_piece))
            board.is_insufficient = is_insufficient
            board.name = name
            self.__add( board )

    def __print_test(self,name):
        return "\n".join([str(n)+".\n"+board.__str__()+"\n"+str(board.is_insufficient)+"\n" for n,board in enumerate(self.tests[name],1)])

    def __repr__(self):
        return self.tests.__repr__()

    def __str__(self):
        return "\n".join([name+":\n\n"+self.__print_test(name)+"\n" for name in self.tests])

    def print_by_name(self,name):
        print("\n",name,":\n",sep="")
        for n,j in enumerate(self.tests[name],1):
            print(n,".",sep="")
            print(j)
            print(j.is_insufficient)
            print()

    def print(self):
        for name in self.tests:
            self.print_by_name(name)
        print("Generated",len(self),"positions.")

    def __compute_combinations(self, pattern, index=0, result=[]):
        """
        Computes the combinations from a pattern.

        e.g pattern=["ab","cde"]->["ac","ad","ae","bc","bd","be"]
        """
        if index == len(pattern):
            return result
        if result == []:
            return self.__compute_combinations(pattern, index+1, pattern[index])
        new_result = []
        for comb in result:
            for piece in pattern[index]:
                new_result.append( "".join(comb+piece) )
        return self.__compute_combinations(pattern, index+1, set(new_result))

    def add_boards_from(self, name, pattern, is_insufficient, base_board):
        """Adds test boards for a black pattern=list of (square, string)."""
        num_pieces = range(len(pattern))
        baseFEN = base_board.fen()

        black_combinations = self.__compute_combinations( [i[1] for i in pattern] )

        for possibillity in black_combinations:
            board = WrappedBoard( baseFEN, name, is_insufficient )
            for i in num_pieces:
                piece = Piece.from_symbol( possibillity[i] )
                sq = pattern[i][0]
                if possibillity[i] == "p" and base_board.is_backrank(sq):
                    sq = board.get_empty_square()
                board.set_piece_at( sq, piece )
            self.__add( board )

        if black_combinations == []:
            board = WrappedBoard( baseFEN, name, is_insufficient )
            self.__add( board )


    def __anticombinations(self, pattern):
        """
        Generates all the combinations of material that occupy the same squares
        and is not covered by the given pattern.
        """
        default_pattern = dict([(i[0],"pbnrq") for i in pattern])

        anti_patterns = set()

        for i in pattern:
            new_pattern = deepcopy(default_pattern)
            new_pattern[i[0]] = "".join(
                    set([j for j in new_pattern[i[0]]])
                    .difference( [j for j in i[1]] )
                )
            anti_patterns.update(  self.__compute_combinations( [new_pattern[j[0]] for j in pattern] )  )

        return anti_patterns

    def __getitem__(self, name):
        return self.tests[name]

    def __len__(self):
        return sum([len(self.tests[name]) for name in self.tests])

    def find_sufficient_subset_composition(self, board):
        """"Finds tests with sufficient material in the given board."""
        for name in self.tests:
            for n,candidate_board in enumerate(self.tests[name]):
                if candidate_board.is_insufficient==False and candidate_board <= board:
                    print(candidate_board.comment+", index:"+str(n),candidate_board,candidate_board.fen(),candidate_board.is_insufficient,sep="\n",end="\n\n")

    def find_tests_with_subset_composition(self, board):
        for name in self.tests:
            for n,candidate_board in enumerate(self.tests[name]):
                if candidate_board <= board:
                    print(candidate_board.comment+", index:"+str(n),candidate_board,candidate_board.fen(),candidate_board.is_insufficient,sep="\n",end="\n\n")


    def randomised_tests(self, percentage=.1, correct=True):
        """
        Picks a percentage of the existing tests and adds some 'random' black
        material to create new tests.
        """

        from random import randint,sample

        limit = int(percentage*len(self))+1

        for n in range(limit):
            board = WrappedBoard()
            board.set_piece_at(A1,Piece.from_symbol("k"))
            white = randint(1,5)
            sq = 48 
            for white_piece in range(white):
                board.set_piece_at(sq,Piece.from_symbol("PBNRQ"[randint(0,4)]))
            black = randint(0,10)
            sq = 8
            for black_piece in range(black):
                board.set_piece_at(sq,Piece.from_symbol("pbnrq"[randint(0,4)]))
                sq += 1
            self.__add(board)        

        if correct:
            self.correct_contradictions()


    def off_by_one(self, correct=True):
        """Generate tests with one more or one less black pieces from the existing tests."""
        newtests = dict()
        for name in self.tests:
            newtests = []
            for cand_board in self.tests[name]:
                sq = cand_board.get_empty_square()
                for piece_type in range(1,6):
                    board = cand_board.deepcopy()
                    board.set_piece_at(sq,Piece(piece_type,False))
                    newtests.append(board)
                board.set_piece_at(sq,None)
                for sq in SquareSet(cand_board.occupied_co[0]):
                    if cand_board.piece_type_at(sq)!=6:
                        board = cand_board.deepcopy()
                        board.is_insufficient = True
                        board.set_piece_at(sq,None)
                        newtests.append(board)

            for board in newtests:
                self.__add( board )

        if correct:
            self.correct_contradictions()


    def correct_contradictions(self):
        """
        Sometimes, when more than two patterns are used and anti-patterns are enabled,
        the generated tests produce contradictions.
        For example, the position 8/8/8/8/8/2Q5/b7/kr6 is generated from the pattern:

                [(A2,"pb"), (B1,"b")],
                black_king_square=A1,
                white=[(C3,"Q")],
                is_insufficient=False

        Strictly speaking, white cannot deliver mate in this position; if black were to
        to respect the pattern and keep their pieces on A2 and B1. Though, a queen on C1
        mates a king on A1 obstructed by a rook on A2.

        Therefore white has sufficient material in the first case and we need to correct
        the value board.is_insufficient for the first board.
        """

        for name in self.tests:
            for n,board in enumerate(self.tests[name]):
                if board.is_insufficient==True and board.has_sufficient_subset():
                    self.tests[name][n].is_insufficient = False


    def __brute_force_black_side(self, king_board, black_side_num):
        """
        Fills the 'king_board' with combinations of black material so that black has at most
        'black_side_num' pieces and return a list with all those combinations.
        """
        def rec(board, black_num):
            if black_num==0:
                return None
            sq = board.get_empty_square()
            for black in "pbnrq":
                temp_board = board.deepcopy()
                temp_board.set_piece_at(sq,Piece.from_symbol(black))
                temp_board.compute_white_composition()
                temp_board.compute_black_composition()
                temp_board.is_insufficient = not self.has_sufficient_subset(temp_board)
                output.append(temp_board)
                if not temp_board.is_insufficient:
                    if black_num==2:
                        rec(temp_board, 1)
                    elif black_num==1:
                        rec(temp_board, 0)
                    else:
                        rec(temp_board, 2)
                else:
                    rec(temp_board, black_num-1)
        output = []
        rec(king_board, black_side_num)
        return output

    def brute_force_and_assess_positions(self, max_black_pieces=5, whites = [["Q"],["P"],["N"],["R"],["B"], ["Q","P"],["R","N"],["R","B"],["N","N"],["B","B"],["B",None,"B"],["B","N"]]):
        """Generates positions with up to 'max_black_pieces' and assess them."""
        king_board = WrappedBoard()
        king_board.set_piece_at(A1,Piece.from_symbol("k"))
        boards = self.__brute_force_black_side(king_board, max_black_pieces)
        for board in boards:
            for white_side in whites:
                temp = board.deepcopy()
                for n,white in enumerate(white_side):
                    temp.set_piece_at(A7+n,Piece.from_symbol(white) if white else None)
                self.add_single_test(
                    "brute-force",
                    temp.fen(),
                    temp.is_insufficient
                    )


    def export_to(self, file_name, preamble="", formatting=lambda x: x, epilogue="", write_type="w"):
        """
        Writes the tests in a file.
        Includes a preamble before the tests, uses a formatting function and
        adds a epilogue after the tests.
        """

        self.correct_contradictions()

        FENs = set()
        refined_tests = []

        for name in self.tests:
            for board in self.tests[name]:
                if board.fen() not in FENs:
                    refined_tests.append(board)
                    FENs.add(board.fen())

        with open(file_name,write_type) as file:
            file.write(preamble)
            for board in refined_tests:
                file.write(formatting(board))
            file.write(epilogue)


    def __piece(self, symbol):
        return Piece.from_symbol(symbol if symbol not in ["D","L"] else "B")

    def __find_posts_to_attack_from(self, target, piece_type):
        board = Board.empty()
        board.set_piece_at( target, self.__piece( piece_type ) )
        if piece_type=="D":
            if target in self.BB_DARK_SQUARES:
                return board.attacks(target)
            else:
                return SquareSet(0)
        elif piece_type=="L":
            if target in self.BB_LIGHT_SQUARES:
                return board.attacks(target)
            else:
                return SquareSet(0)
        else:
            return board.attacks(target)

    def __get_white_configurations(self, king, escape_squares, white_minor_pieces):
        """
        Generates possible white configurations that minimise the squares
        available to the king to which he can escape to when up to two
        white minor pieces are given.
        """
        boards = []

        for n,checker in enumerate(white_minor_pieces):
            for sq in self.__find_posts_to_attack_from(king, checker):
                board = WrappedBoard('8/8/8/8/8/8/8/8 b - - 0 1', "", True)
                board.set_piece_at( king, Piece(6, False) )
                board.set_piece_at( sq, self.__piece(checker) )
                board.checker = checker
                board.checker_sq = sq
                if len(white_minor_pieces)==2:
                    board.not_checker = white_minor_pieces[(1+n)%2]
                boards.append( board )

        if len(white_minor_pieces) == 1:
            output = set()
            for board in boards:
                if board.checker != "N" and board.bishops & int(self.BB_BORDER) == 0:
                    # discard some cases to reduce the search space
                    continue
                output.add(board.fen())
            return [WrappedBoard(fen) for fen in output]

        output = set()
        for board in boards:
            checker = board.checker
            checker_sq = board.checker_sq
            not_checker = board.not_checker
            for esc_sq in escape_squares:
                for sq in self.__find_posts_to_attack_from(esc_sq, not_checker):
                    if checker_sq == sq:
                        continue
                    temp_board = board.deepcopy()
                    temp_board.set_piece_at( sq, self.__piece(not_checker) )
                    if temp_board.is_legal( Move(king, sq) ) or temp_board.is_legal( Move(king, checker_sq) ) or not temp_board.is_check() or len(temp_board.checkers())==2:
                        continue
                    if white_minor_pieces == ['D','D'] or white_minor_pieces == ['L','L']:
                        if sq in SquareSet.ray(king, checker_sq) or king in temp_board.attacks(sq)&temp_board.attacks(checker_sq):
                            # discard some cases to reduce the total number of cases
                            continue
                    if white_minor_pieces == ['D','L']:
                        if temp_board.occupied_co[1]&0x007e_7e7e_7e7e_7e00!=0:
                            # discard some cases to reduce the total number of cases
                            continue
                    output.add( temp_board.fen() )
            if white_minor_pieces == ['D','N'] or white_minor_pieces == ['L','N']: #double check
                for sq in self.__find_posts_to_attack_from(king, not_checker):
                    if checker_sq == sq:
                        continue
                    temp_board = board.deepcopy()
                    temp_board.set_piece_at( sq, self.__piece(not_checker) )
                    if temp_board.is_legal( Move(king, sq) ) or temp_board.is_legal( Move(king, checker_sq) ) or not temp_board.is_check():
                        continue
                    if checker == "N":
                        bishop, knight = sq, checker_sq
                    else:
                        knight, bishop = sq, checker_sq
                    if bishop not in self.BB_BORDER:
                        # discard some cases to reduce the total number of cases
                        continue
                    if len(SquareSet.between(king,bishop)&temp_board.attacks(knight)) == 0:
                        continue
                    output.add(temp_board.fen())

        return [WrappedBoard(fen) for fen in output]


    def __can_piece_save_king(self, board, piece, squares_to_stop_check):
        """
        Is the piece able to attack one of the 'squares_to_stop_check'
        and save their king?
        """
        for sq in squares_to_stop_check:
            try:
                board.find_move(piece, sq)
                return True
            except ValueError:
                pass
        return False            

    def __get_black_configurations(self, king, escape_squares, white_board):
        """
        Fills the empty squares around the king with black pieces
        so white mates and returns a board with the found pattern.
        """
        white_board.black_pattern = []
        checkers = white_board.checkers()

        for checker_sq in checkers:
            try:
                white_board.find_move(king, checker_sq)
                return white_board
            except ValueError:
                pass

        available_squares = [sq for sq in escape_squares if not white_board.is_attacked_by(True,sq)]
        
        if popcount(checkers)>1:
            for sq in available_squares:
                white_board.black_pattern.append(
                    (sq,"bnrq") if white_board.is_backrank(sq) else (sq,"pnbrq")
                    )
            return white_board

        squares_to_stop_check = (
            SquareSet.from_square(checker_sq)|white_board.attacks(checker_sq)
            )&(~white_board.occupied_co[0])
        
        for sq in available_squares:
            white_board.set_piece_at(sq, Piece.from_symbol("p"))
        
        for black_piece in available_squares:
            possible_pieces = ""

            if black_piece not in self.BB_BACKRANKS:
                white_board.set_piece_at(black_piece,Piece.from_symbol("p"))
                if self.__can_piece_save_king(white_board, black_piece, squares_to_stop_check)==False:
                    possible_pieces += "p"

            white_board.set_piece_at(black_piece,Piece.from_symbol("n"))
            if self.__can_piece_save_king(white_board, black_piece, squares_to_stop_check)==False:
                possible_pieces += "n"

            white_board.set_piece_at(black_piece,Piece.from_symbol("q"))
            if self.__can_piece_save_king(white_board, black_piece, squares_to_stop_check)==False:
                possible_pieces += "brq"
            else:
                white_board.set_piece_at(black_piece,Piece.from_symbol("b"))
                if self.__can_piece_save_king(white_board, black_piece, squares_to_stop_check)==False:
                    possible_pieces += "b"

                white_board.set_piece_at(black_piece,Piece.from_symbol("r"))
                if self.__can_piece_save_king(white_board, black_piece, squares_to_stop_check)==False:
                    possible_pieces += "r"

            white_board.set_piece_at(black_piece,Piece.from_symbol("p"))

            if possible_pieces == "":
                white_board.black_pattern == None
                break
            else:
                white_board.black_pattern.append((black_piece,possible_pieces))

        for sq in available_squares:
            white_board.set_piece_at(sq, None) 

        return white_board


    def print_patterns(self, king_square, white_pieces):
        """The current implementation only works for minor pieces."""
        board=Board.empty()
        board.set_piece_at(king_square,Piece.from_symbol("k"))
        escape_squares = board.attacks(king_square)
        white_boards = self.__get_white_configurations( king_square, escape_squares, white_pieces)
        patterns = list( (board, self.__get_black_configurations( king_square, escape_squares, board ).black_pattern)  for board in white_boards )
        output = []
        for board, pattern in patterns:
            nxt = [(square_name(i[0]).upper(),"".join([lt if lt!="b" else ("d" if i[0] in self.BB_DARK_SQUARES else "l") for lt in i[1]])) for i in pattern], [square_name(sq).upper() for sq in SquareSet(board.occupied_co[1])]
            if pattern and nxt not in output:
                output.append(nxt)
                s = ""
                for j in nxt[0]:
                    s+=j[1]
                print(s,nxt)
        return output
    

    def generate_patterns( self, white_sides = [ ['D'], ['N'], ['D','N'], ['N','N'], ['D','L'], ['D','D'] ], king_squares = [A1,A2,A3,A4] ):
        """
        Finds mating patterns for the given white sides.
        The current implementation only works for minor pieces.
        """
        ## D=dark square bishop, L=light square bishop
        for king in king_squares:
            board = WrappedBoard('8/8/8/8/8/8/8/8 b - - 0 1')
            board.set_piece_at(king,Piece(6,False))
            escape_squares = board.attacks(king)
            for white_side in white_sides:
                white_configurations = self.__get_white_configurations(king, escape_squares, white_side)
                for white_configuration in white_configurations:
                    board_with_pattern = self.__get_black_configurations(king, escape_squares, white_configuration)
                    white_configuration.compute_white_composition()
                    self.add_boards_from(
                        str(white_configuration.white_composition).replace("'","").replace(", ","-"),
                        board_with_pattern.black_pattern,
                        False,
                        white_configuration
                        )






if __name__ == "__main__":

    start = time()

    print("Test generation is underway...")

    insufficient_material = GenerateTestsFromPatterns()


    #print("Generating patterns with knights and bishops...",end="")
    #insufficient_material.generate_patterns()
    #print(" (",len(insufficient_material)," positions found)", sep="")
    #print("Continuing with more general patterns")


    insufficient_material.add_pattern(
        "white=0",
        [],
        is_insufficient=True,
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white=0",
        [(A2,"q"),(D6,"rpn"),(F5,"bq")],
        is_insufficient=True,
        generate_insufficient=False
        )


    insufficient_material.add_pattern(
        "white=Q",
        [(A2,"pr")],
        black_king_square=A1,
        white=[(C1,"Q")]
        )
    insufficient_material.add_pattern(
        "white=Q",
        [(A2,"pb"), (B1,"b")],
        black_king_square=A1,
        white=[(C3,"Q")]
        )

    insufficient_material.add_pattern(
        "white=R",
        [(A7,"pr"),(B7,"pn")],
        black_king_square=A8,
        white=[(C8,"R")]
        )

    insufficient_material.add_pattern(
        "white=B",
        [(A2,"pb"),(B1,"b")],
        white=[(C3,"B")]
        )
    insufficient_material.add_pattern(
        "white=B",
        [(A4,"pb"),(B3,"pb"),(A2,"pbrq"),(B2,"pbnrq")],
        black_king_square=A3,
        white=[(C5,"B")]
        )
    insufficient_material.add_pattern(
        "white=B",
        [(A4,"p"),(B3,"p"),(A1,"b"),(B2,"n")],
        black_king_square=A3,
        white=[(C5,"B")],
        is_insufficient=True,
        generate_insufficient=False,
        )

    insufficient_material.add_pattern(
        "white=N",
        [(B2,"pbn"),(A2,"pnr"),(B1,"bnrq")],
        white=[(B3,"N")]
        )
    insufficient_material.add_pattern(
        "white=N",
        [(B2,"pbn"),(A2,"pbnrq"),(B1,"nr")],
        white=[(C2,"N")]
        )
    insufficient_material.add_pattern(
        "white=N",
        [(B2,"p"),(A2,"p"),(B3,"p")],
        black_king_square=A3,
        white=[(B5,"N")],
        is_insufficient=True,
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white=N",
        [(B5,"pbn"),(A5,"pnr"),(A3,"pbnrq"),(B3,"pbnrq"),(B4,"pbnrq")],
        black_king_square=A4,
        white=[(B6,"N")]
        )


    insufficient_material.add_pattern(
        "white=P",
        [(A2,"pr")],
        black_king_square=A1,
        white=[(C2,"P")],
        dont_spam=True
        )
    insufficient_material.add_pattern(
        "white=P",
        [(A2,"pb"), (B1,"b")],
        black_king_square=A1,
        white=[(C3,"P")],
        dont_spam=True
        )
    insufficient_material.add_pattern(
        "white=P",
        [(B2,"pbn"),(A2,"pnr"),(B1,"bnrq")],
        white=[(B3,"P")],
        dont_spam=True
        )
    insufficient_material.add_pattern(
        "white=P",
        [(B2,"pbn"),(A2,"pbnrq"),(B1,"nr")],
        white=[(C2,"P")],
        dont_spam=True
        )
    insufficient_material.add_pattern(
        "white=P",
        [(B2,"p"),(A2,"p"),(B3,"p")],
        black_king_square=A3,
        white=[(B5,"P")],
        is_insufficient=True,
        generate_insufficient=False,
        dont_spam=True
        )
    insufficient_material.add_pattern(
        "white=P",
        [(B5,"pbn"),(A5,"pnr"),(A3,"pbnrq"),(B3,"pbnrq"),(B4,"pbnrq")],
        black_king_square=A4,
        white=[(B6,"P")],
        dont_spam=True
        )


    insufficient_material.add_pattern(
        "white>=2 & queen",
        [],
        black_king_square=H8,
        white=[(H7,"Q"),(F6,"N")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white>=2 & pawn",
        [],
        black_king_square=H8,
        white=[(H7,"P"), (G7,"P"), (H6,"Q")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white>=2 & rook",
        [],
        white=[(H1,"R"),(G2,"R")],
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white>=2 & rook",
        [],
        white=[(B1,"R"),(C3,"N")],
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white>=2 & rook",
        [],
        white=[(H5,"R"),(H4,"B")],
        is_insufficient=True,
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white>=2 & rook",
        [(A7,"pn")],
        black_king_square=A8,
        white=[(B8,"R"),(D6,"B")],
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white>=2 & rook",
        [(C2,"pbrq")],
        black_king_square=B1,
        white=[(A1,"R"),(C3,"B")],
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white>=2 & rook",
        [],
        white=[(B1,"R"),(C4,"B"),(D3,"B")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=2 vs lone king",
        [],
        white=[(C2,"B"),(C4,"B"),(C6,"B"),(C8,"B")],
        is_insufficient=True,
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=2N",
        [(B2,"pbn")],
        white=[(B3,"N"),(C3,"N")]
        )

    insufficient_material.add_pattern(
        "white=2B bishop pair",
        [(A2,"pb")],
        white=[(C2,"B"),(C3,"B")]
        )
    insufficient_material.add_pattern(
        "white=2B bishop pair",
        [(B4,"pbn"),(A4,"pbrq")],
        black_king_square=A3,
        white=[(C1,"B"),(C4,"B")]
        )

    insufficient_material.add_pattern(
        "white=2B same colour",
        [(A2,"pbn"),(B1,"bn")],
        white=[(B2,"B"),(C3,"B")]
        )
    insufficient_material.add_pattern(
        "white=2B same colour",
        [(A4,"pbn"),(B3,"pbn"),(A2,"pbrq")],
        black_king_square=A3,
        white=[(B4,"B"),(C3,"B")]
        )

    insufficient_material.add_pattern(
        "white=B+N",
        [(A2,"pbnrq"),(B1,"pbnrq")],
        black_king_square=A1,
        white=[(C2,"N"),(H8,"B")]
        )
    insufficient_material.add_pattern(
        "white=B+N",
        [(A2,"pb")],
        white=[(D2,"N"),(C3,"B")]
        )
    insufficient_material.add_pattern(
        "white=B+N",
        [(B4,"pbn"),(A2,"pnr")],
        black_king_square=A3,
        white=[(C2,"B"),(C4,"N")]
        )
    insufficient_material.add_pattern(
        "white=B+N",
        [(B1,"bnrq"),(B2,"pbnrq"),(A2,"pnr")],
        black_king_square=A1,
        white=[(C3,"B"),(B3,"N")]
        )
    insufficient_material.add_pattern(
        "white=B+N",
        [(A2,"pbnrq"),(B2,"pbnrq"),(B3,"pbnrq"),(A4,"pbnrq")],
        black_king_square=A3,
        white=[(C5,"B"),(C2,"N")]
        )
    insufficient_material.add_single_test(
        "white=B+N",
        "8/8/8/8/8/1NB5/1b1b1b2/k7 b - - 0 1",
        is_insufficient=True
        )
    insufficient_material.add_single_test(
        "white=B+N",
        "8/8/8/b1B1b3/1b1b1b2/k7/2N5/8 b - - 0 1",
        is_insufficient=True
        )
    insufficient_material.add_single_test(
        "white=B+N",
        "8/8/8/1bBb4/bpb1b3/k7/2N5/8 b - - 0 1",
        is_insufficient=True
        )


    insufficient_material.add_pattern(
        "white=3B",
        [],
        white=[(C2,"B"),(C3,"B"),(C4,"B")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=3N",
        [],
        white=[(C2,"N"),(C3,"N"),(C4,"N")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=2N+B",
        [],
        white=[(C1,"B"),(C2,"N"),(C3,"N")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=2B+N bishop pair",
        [],
        white=[(D2,"N"),(C3,"B"),(B1,"B")],
        generate_insufficient=False
        )

    insufficient_material.add_pattern(
        "white=2B+N same colour",
        [],
        white=[(C1,"B"),(A3,"B"),(C3,"N")],
        is_insufficient=True,
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white=2B+N same colour",
        [(H5,"pbnrq")],
        white=[(C1,"B"),(B2,"B"),(C3,"N")],
        generate_insufficient=False
        )
    insufficient_material.add_pattern(
        "white=2B+N same colour",
        [(H4,"pbnrq")],
        white=[(C1,"B"),(B2,"B"),(C3,"N")],
        generate_insufficient=False
        )


    insufficient_material.add_pattern(
        "white>=4",
        [(D3,"q"),(C4,"q")],
        black_king_square=D4,
        white=[(D1,"N"),(D7,"N"),(E5,"B"),(F6,"N")],
        generate_insufficient=False
        )


    insufficient_material.add_tests_from_white_pattern(
        "white=Q+anything",
        [(H7,"Q"),(G6,"PBNRQ")]
        )
    insufficient_material.add_tests_from_white_pattern(
        "white=P+anything",
        [(H7,"P"),(G6,"PBNRQ")]
        )


    print("All the patterns got processed in "+str(time()-start)+"s.")
    print(len(insufficient_material),"tests created so far.")


##    print("Generating tests with off by one pieces...")
##    insufficient_material.off_by_one(correct=False)
##    print(len(insufficient_material),"tests created so far.")


    print("Generating all tests with 5 or less black pieces")
    insufficient_material.brute_force_and_assess_positions(5)
    print(len(insufficient_material),"tests created so far.")


    print("Generating more random tests...")
    insufficient_material.randomised_tests(percentage=.9,correct=False)
    print(len(insufficient_material),"tests created so far.")


    print("Writing tests to disk...")
    insufficient_material.export_to(
        abspath("./horde_white_insufficient_material_tests"),
        "",
        lambda board: board.fen()+','+str(board.is_insufficient).lower()+','+board.comment+'\n',
        ""
        )

    input(str(len(insufficient_material))+" tests were generated at 'white_insufficient_material_horde' in "+str(time()-start)+"s.")















