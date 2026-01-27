import pytest

from jmux.pda import PushDownAutomata
from jmux.types import Mode, State


@pytest.mark.parametrize(
    "start_state",
    [
        State.START,
        State.END,
        State.ERROR,
        State.EXPECT_KEY,
        State.PARSING_STRING,
    ],
)
def test_pda_initial_state(start_state: State):
    pda = PushDownAutomata[Mode, State](start_state)
    assert pda.state == start_state


@pytest.mark.parametrize(
    "start_state",
    [
        State.START,
        State.END,
    ],
)
def test_pda_initial_stack_is_empty(start_state: State):
    pda = PushDownAutomata[Mode, State](start_state)
    assert pda.stack == []
    assert pda.top is None


@pytest.mark.parametrize(
    "new_state",
    [
        State.EXPECT_KEY,
        State.EXPECT_COLON,
        State.EXPECT_VALUE,
        State.PARSING_STRING,
        State.END,
    ],
)
def test_pda_set_state(new_state: State):
    pda = PushDownAutomata[Mode, State](State.START)
    pda.set_state(new_state)
    assert pda.state == new_state


def test_pda_set_state_multiple_times():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.set_state(State.EXPECT_KEY)
    assert pda.state == State.EXPECT_KEY
    pda.set_state(State.PARSING_STRING)
    assert pda.state == State.PARSING_STRING
    pda.set_state(State.END)
    assert pda.state == State.END


@pytest.mark.parametrize(
    "mode",
    [
        Mode.ROOT,
        Mode.OBJECT,
        Mode.ARRAY,
    ],
)
def test_pda_push_single(mode: Mode):
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(mode)
    assert pda.stack == [mode]
    assert pda.top == mode


def test_pda_push_multiple():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.push(Mode.OBJECT)
    pda.push(Mode.ARRAY)
    assert pda.stack == [Mode.ROOT, Mode.OBJECT, Mode.ARRAY]
    assert pda.top == Mode.ARRAY


def test_pda_pop_single():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    result = pda.pop()
    assert result == Mode.ROOT
    assert pda.stack == []
    assert pda.top is None


def test_pda_pop_multiple():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.push(Mode.OBJECT)
    pda.push(Mode.ARRAY)

    result1 = pda.pop()
    assert result1 == Mode.ARRAY
    assert pda.top == Mode.OBJECT

    result2 = pda.pop()
    assert result2 == Mode.OBJECT
    assert pda.top == Mode.ROOT

    result3 = pda.pop()
    assert result3 == Mode.ROOT
    assert pda.top is None


def test_pda_pop_empty_stack_raises_index_error():
    pda = PushDownAutomata[Mode, State](State.START)
    with pytest.raises(IndexError, match="PDA stack is empty"):
        pda.pop()


def test_pda_pop_after_emptying_stack_raises_index_error():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.pop()
    with pytest.raises(IndexError, match="PDA stack is empty"):
        pda.pop()


def test_pda_push_pop_interleaved():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.push(Mode.OBJECT)
    assert pda.pop() == Mode.OBJECT

    pda.push(Mode.ARRAY)
    pda.push(Mode.OBJECT)
    assert pda.stack == [Mode.ROOT, Mode.ARRAY, Mode.OBJECT]
    assert pda.top == Mode.OBJECT

    assert pda.pop() == Mode.OBJECT
    assert pda.pop() == Mode.ARRAY
    assert pda.top == Mode.ROOT


def test_pda_top_does_not_modify_stack():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.push(Mode.OBJECT)

    _ = pda.top
    _ = pda.top
    _ = pda.top

    assert pda.stack == [Mode.ROOT, Mode.OBJECT]


def test_pda_stack_property_returns_internal_list():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    stack = pda.stack
    assert stack is pda._stack


def test_pda_with_string_types():
    pda = PushDownAutomata[str, str]("initial")
    assert pda.state == "initial"
    pda.set_state("next")
    assert pda.state == "next"

    pda.push("context1")
    pda.push("context2")
    assert pda.top == "context2"
    assert pda.pop() == "context2"


def test_pda_with_int_types():
    pda = PushDownAutomata[int, int](0)
    assert pda.state == 0
    pda.set_state(1)
    assert pda.state == 1

    pda.push(100)
    pda.push(200)
    assert pda.top == 200
    assert pda.stack == [100, 200]


def test_pda_many_push_operations():
    pda = PushDownAutomata[Mode, State](State.START)
    for _ in range(100):
        pda.push(Mode.OBJECT)
    assert len(pda.stack) == 100
    assert pda.top == Mode.OBJECT


def test_pda_many_pop_operations():
    pda = PushDownAutomata[int, int](0)
    for i in range(100):
        pda.push(i)

    for i in range(99, -1, -1):
        assert pda.pop() == i

    assert pda.stack == []
    assert pda.top is None


def test_pda_top_returns_last_pushed_incrementally():
    pda = PushDownAutomata[Mode, State](State.START)
    assert pda.top is None

    pda.push(Mode.ROOT)
    assert pda.top == Mode.ROOT

    pda.push(Mode.OBJECT)
    assert pda.top == Mode.OBJECT

    pda.push(Mode.ARRAY)
    assert pda.top == Mode.ARRAY


def test_pda_state_is_readable_property():
    pda = PushDownAutomata[Mode, State](State.START)
    assert pda.state == State.START

    pda.set_state(State.EXPECT_KEY)
    state_value = pda.state
    assert state_value == State.EXPECT_KEY
    assert isinstance(state_value, State)


def test_pda_typical_json_parsing_flow():
    pda = PushDownAutomata[Mode, State](State.START)

    pda.set_state(State.EXPECT_KEY)
    pda.push(Mode.ROOT)
    assert pda.state == State.EXPECT_KEY
    assert pda.top == Mode.ROOT

    pda.set_state(State.PARSING_KEY)
    assert pda.state == State.PARSING_KEY

    pda.set_state(State.EXPECT_COLON)
    pda.set_state(State.EXPECT_VALUE)
    pda.set_state(State.PARSING_STRING)

    pda.push(Mode.ARRAY)
    assert pda.stack == [Mode.ROOT, Mode.ARRAY]

    pda.set_state(State.EXPECT_COMMA_OR_EOC)
    pda.pop()
    assert pda.top == Mode.ROOT

    pda.set_state(State.END)
    pda.pop()
    assert pda.stack == []
    assert pda.state == State.END


def test_pda_stack_returns_full_contents():
    pda = PushDownAutomata[Mode, State](State.START)
    pda.push(Mode.ROOT)
    pda.push(Mode.OBJECT)
    pda.push(Mode.ARRAY)

    stack_contents = pda.stack
    assert stack_contents == [Mode.ROOT, Mode.OBJECT, Mode.ARRAY]
    assert len(stack_contents) == 3
