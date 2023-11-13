from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from cfg import core_config
from core.description.description_models import s_main, display, energy, camera, performance


def get_goods_desc(model: list):
    sample = select(
        s_main.c.title,
        s_main.c.release_date,
        s_main.c.category,
        display.c.d_size,
        display.c.display_type,
        display.c.refresh_rate,
        display.c.resolution,
        energy.c.capacity,
        energy.c.max_charge_power,
        energy.c.fast_charging,
        camera.c.lenses,
        camera.c.megapixels_front,
        performance.c.chipset,
        performance.c.total_score,
        s_main.c.advantage,
        s_main.c.disadvantage) \
        .where(
        (s_main.c.title.in_(model)) &
        (s_main.c.title == display.c.title) &
        (s_main.c.title == energy.c.title) &
        (s_main.c.title == camera.c.title) &
        (s_main.c.title == performance.c.title)
    )
    engine = create_engine(url=core_config.phones_desc_db)
    with Session(engine) as session:
        description = session.execute(sample).fetchone()
    return description


response = get_goods_desc('Realme C25Y')
for line in response:
    print(line)
