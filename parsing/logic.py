import importlib.util
import sys
from pathlib import Path

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import delete_harvest_strings_by_vsl_id
from api_service.schemas import ParsingRequest
from config import BASE_DIR
from models import Vendor



async def parsing_core(redis: Redis,
                       data: ParsingRequest,
                       vendor: Vendor,
                       session: AsyncSession,
                       function_name: str) -> dict:
    module_path = Path(f"{BASE_DIR}/parsing/sources/{function_name}.py")
    if not module_path.exists():
        raise FileNotFoundError(f"Функция {module_path} не найдена")
    module_name = f"parsing.sources.{function_name}"
    module = importlib.import_module(module_name)
    parser_class = getattr(module, "BaseParser")
    pars_obj = parser_class(redis, data, vendor, session)
    await pars_obj.run()
    try:
        await delete_harvest_strings_by_vsl_id(session=session, vsl_id=data.vsl_id)
        collected_data: dict = await pars_obj.process()
    finally:
        await pars_obj.browser.close()
        await pars_obj.playwright.stop()
    # if len(collected_data['data']) > 0:
    #     await append_info(session=session, data=collected_data)
    return collected_data
