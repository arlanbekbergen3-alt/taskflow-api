import asyncio
import time


async def fetch_rate(bank_name: str, delay: int) -> float:
    print(f"[Начало] Запрос к {bank_name}")
    await asyncio.sleep(delay)
    print (f"[Конец] {bank_name} вернул курс")
    return 90

async def main():
    banks = [("SberBank", 3), ("AlfaBank", 1), ("T-Bank", 2)]
    start_time = time.perf_counter()
    tasks = [fetch_rate(name, delay) for name, delay in banks]
    print("Запуск всех запросов одновременно")
    rates = await asyncio.gather(*tasks)

