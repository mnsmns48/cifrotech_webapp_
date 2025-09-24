from aiogram.fsm.state import State, StatesGroup


class UserMainMenu(StatesGroup):
    start = State()
    walking_dork = State()
