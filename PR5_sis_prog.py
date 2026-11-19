import aiohttp
import asyncio
import json
from datetime import datetime

BRAND_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{}?format=json"
SPEC_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{}?format=json"

BRAND_NAMES = ["honda", "toyota", "bmw"]
VIN_CODES = ["1HGCM82633A004352", "JTDKN3DU0A0000001"]
REQUEST_TIMEOUT = 5
COLLECT_INTERVAL = 600

request_limit = asyncio.Semaphore(3)


async def fetch_data(url, session):
    async with request_limit:
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json(content_type=None)
                print(f"Ошибка {response.status} при запросе {url}")
        except asyncio.TimeoutError:
            print(f"Таймаут при запросе {url}")
        except Exception as error:
            print(f"Ошибка {error} при запросе {url}")
    return None


async def get_cars_data():
    async with aiohttp.ClientSession() as session:
        brand_responses, spec_responses = await asyncio.gather(
            asyncio.gather(*(fetch_data(BRAND_API_URL.format(name), session) for name in BRAND_NAMES)),
            asyncio.gather(*(fetch_data(SPEC_API_URL.format(vin), session) for vin in VIN_CODES)),
        )

    brands = []
    for brand_name, response in zip(BRAND_NAMES, brand_responses):
        results = response["Results"] if response else []
        brands.append({"brand": brand_name,
                       "models": [item["Model_Name"] for item in results][:5]})

    specs = []
    for response in spec_responses:
        if response:
            car = response["Results"][0]
            specs.append({"brand": car.get("Make"), "model": car.get("Model"),
                          "year": car.get("ModelYear"), "body": car.get("BodyClass"),
                          "fuel": car.get("FuelTypePrimary"), "engine_l": car.get("DisplacementL")})

    return {"brands": brands, "specs": specs, "timestamp": datetime.now().isoformat()}


def save_data(data):
    filename = f"cars_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(filename, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)
    return filename


async def main():
    while True:
        data = await get_cars_data()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("Сохранено в файл:", save_data(data))
        await asyncio.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
