from fractions import Fraction


RationalInput = int | str | Fraction


def parse_rational(value: RationalInput) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) not in (int, str):
        raise ValueError(f'expected an exact rational, got {value!r}')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f'invalid rational: {value!r}') from error


def to_rational_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def from_rational_pair(pair: object) -> Fraction:
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError('a rational pair needs a numerator and denominator')
    numerator, denominator = pair
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise ValueError('a rational pair needs integers and a positive denominator')
    return Fraction(numerator, denominator)
