import re


def parse_products_from_line(text):
    # Разбиваем текст на строки
    lines = text.splitlines()

    products = []
    for line in lines:
        # Убираем лишние пробелы
        line = line.strip()
        if not line:
            continue  # Пропускаем пустые строки

        # Ищем последнее число от 4 до 6 цифр в строке
        match = re.search(r'(\d{4,6})\s*$', line)
        if match:
            price = int(match.group(1))  # Извлекаем цену
            name = line[:match.start()].strip()  # Всё до цены — название товара
            products.append({
                "name": name,
                "price": price
            })

    return products


# Пример строки
product_line = """
🇮🇳S23 S911B 8/128 Black(544153) 38800
🇮🇳S23 S911B 8/128 Cream (536508) 38100
🇮🇳S23 S911B 8/128 Lavender CL(536509) 38300
🇮🇳S23 SM-S911 8/128 Green(537518) 38300
🇮🇳S23 SM-S911 8/256 Green(537519) 42400
🇮🇳S23 SM-S911 8/256 Cream(537521) 42200
🇰🇼S23 Ultra S918B 12/256 Black KW(536512) 64100
🇨🇳S24 S9210 12/256 Marble Gray CN(536518) 52700
🇰🇼S24 S9210 12/256 Onyx Black(611861) 52700
🇭🇰S24 S9210 8/256 Marble Gray HK(536521) 46500
🇰🇼S24 FE S721B 8/256 Graphite(576341) 37100
🇰🇼S24 FE S721B 8/256 Gray(576342) 37100
🇰🇼S24 FE S721B 8/256 Mint(576343) 37200
🇰🇼S24 S921B 8/256 Black(537550) 46200
🇿🇦S24 Ultra S928B 12/1Tb Titanium Black(537559) 97200
S24 Ultra S928B 12/1Tb Titanium Violet(537563) 97200
🇪🇺S24 Ultra S928B 12/1Tb Titanium Yellow(537564) 97200
🇰🇼S24 Ultra 12/256 Grey SM-S928B/DS(537556) 69800
🇰🇼S24 Ultra 12/256 Titanium Violet S928B(537557) 69800
🇿🇦S24 Ultra 12/256 Titanium YellowS92 8B(537558) 69800
🇨🇱S24 Ultra S928B 12/512 Titanium Violet(537565) 76700
🇨🇱S24 Ultra S928B 12/512 Titanium Black(537566) 76000
🇨🇱S24 Ultra S928B 12/512 Titanium Gray(537567) 76800
🇮🇳S24+ S926B 12/256 Onyx Black (536552) 51200
🇮🇳S24+ S926B 12/256 Amber Yellow(537570) 52500
🇮🇳S24+ S926B 12/256 Cobalt Violet(537571) 52700
🇮🇳S24+ S926B 12/256 Marble Gray(537572) 52700
🇿🇦S24+ S926B 12/512 Onyx Black(537577) 62000
🇹🇭Z Flip 6 F741B 12/256 Blue(559818) 59100
🇹🇭Z Flip 6 F741B 12/256 Silver Shadow(559820) 58900
🇰🇼S25 Ultra S938B 12/256 Titanium Black(604070) 82900
🇰🇼S25 Ultra S938B 12/256 Titanium Gray(604071) 83200
🇰🇼S25 Ultra S938B 12/256 Titanium Whitesilver(604074) 82700
🇰🇼S25 Ultra S938B 12/256 Titanium Silverblue(604075) 83200
🇰🇼S25 Ultra S938B 12/512 Titanium Silverblue(604079) 92500
🇰🇼S25 Ultra S938B 12/512 Titanium Gray(604080) 92000
🇰🇼S25 Ultra S938B 12/512 Whitesilver(604084) 92300
🇰🇼S25 Ultra S938B 12/1Tb Titanium Gray(604087) 109200
🇰🇼S25 Ultra S938B 12/1Tb Titanium Jadegreen(604088) 110600
🇰🇼S25 Ultra S938B 12/1Tb Titanium Whitesilver(604092) 110600
🇰🇼S25 Ultra S9380 16/1Tb Titanium Whitesilver(620375) 114700
🇰🇼S25+ S936B 12/256 Icyblue(604100) 67200
🇰🇼S25+ S936B 12/256 Silver Shadow(604101) 67200
🇰🇼S25+ S936B 12/512 Navy(604107) 74600
🇰🇼S25+ S936B 12/512 Mint(604109) 74600

"""

# Вызов функции
result = parse_products_from_line(product_line)
for product in result:
    print(product)