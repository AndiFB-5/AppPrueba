import sys
import os
import csv
import io
import re
import json
from datetime import datetime, timezone, timedelta

MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

def format_num(val):
    try:
        val_float = float(val)
        if val_float.is_integer():
            return str(int(val_float))
        return str(round(val_float, 2))
    except (ValueError, TypeError):
        return str(val)

def parse_date(date_str, adjust_utc_to_utc3=False):
    dt = None
    try:
        dt = datetime.fromisoformat(str(date_str))
    except Exception:
        try:
            dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now()

    if adjust_utc_to_utc3:
        dt = dt - timedelta(hours=3)

    wednesday_date = dt.date() - timedelta(days=dt.weekday() - 2)
    fecha_miercoles = str(wednesday_date)
    mes = MESES.get(wednesday_date.month, '')
    formatted_order_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    return mes, fecha_miercoles, formatted_order_date

def process_single_line(line_str, adjust_utc=False, delimiter=","):
    line_str = line_str.strip()
    if not line_str:
        return []

    # Find JSON array enclosed in [...]
    json_match = re.search(r'(\[.*\])', line_str)
    if not json_match:
        return []

    json_raw = json_match.group(1)
    
    before = line_str[:json_match.start()].strip()
    while before.endswith(',') or before.endswith('"') or before.endswith('\t'):
        before = before[:-1].strip()

    after = line_str[json_match.end():].strip()
    while after.startswith(',') or after.startswith('"') or after.startswith('\t'):
        after = after[1:].strip()

    # Detect delimiter in before
    if '\t' in before:
        parts_before = [p.strip() for p in before.split('\t')]
    else:
        parts_before = [p.strip() for p in list(csv.reader([before]))[0]] if before else []

    # Handle total_price in after
    if '\t' in after:
        total_price = [p.strip() for p in after.split('\t') if p.strip()][-1] if after else "0"
    elif ',' in after:
        total_price = [p.strip() for p in list(csv.reader([after]))[0] if p.strip()][-1] if after else "0"
    else:
        total_price = after.strip() if after else "0"

    if len(parts_before) >= 6:
        # Format with MES and Fecha Miercoles already present
        order_id = parts_before[0]
        customer_name = parts_before[1]
        mes = parts_before[2]
        fecha_miercoles = parts_before[3].split()[0] # Sin hora
        order_date = parts_before[4]
        metodo_pago = parts_before[5]
    elif len(parts_before) >= 4:
        # Format: [order_id, customer_name, order_date, metodo_pago]
        order_id = parts_before[0]
        customer_name = parts_before[1]
        order_date_raw = parts_before[2]
        metodo_pago = parts_before[3]
        mes, fecha_miercoles, order_date = parse_date(order_date_raw, adjust_utc_to_utc3=adjust_utc)
    else:
        order_id = parts_before[0] if len(parts_before) > 0 else ""
        customer_name = parts_before[1] if len(parts_before) > 1 else ""
        order_date_raw = parts_before[2] if len(parts_before) > 2 else ""
        metodo_pago = parts_before[3] if len(parts_before) > 3 else ""
        mes, fecha_miercoles, order_date = parse_date(order_date_raw, adjust_utc_to_utc3=adjust_utc)

    # Clean JSON string (handle doubled quotes in CSV, escaped backslashes, etc.)
    json_clean = json_raw.replace('""', '"').replace(r'\"', '"')
    try:
        items = json.loads(json_clean)
    except Exception:
        return []

    if not isinstance(items, list):
        return []

    output_rows = []
    for item in items:
        prod_name = item.get('producto') or item.get('product_name') or ''
        qty = item.get('cantidad') or item.get('quantity') or 0
        unit_price = item.get('precio_unitario') or item.get('item_price') or item.get('price') or 0
        try:
            item_total = float(qty) * float(unit_price)
        except Exception:
            item_total = 0

        out_fields = [
            order_id,
            customer_name,
            mes,
            fecha_miercoles,
            order_date,
            metodo_pago,
            str(prod_name),
            format_num(qty),
            format_num(unit_price),
            format_num(item_total),
            format_num(total_price)
        ]
        output_rows.append(delimiter.join(out_fields))

    return output_rows

def desanidar_texto(texto, adjust_utc=False, delimiter=",", include_header=False):
    lines = [line.strip() for line in texto.splitlines() if line.strip()]
    results = []
    
    if include_header:
        headers = [
            'order_id', 'customer_name', 'MES', 'Fecha Miercoles',
            'order_date', 'metodo_pago', 'product_name', 'quantity',
            'item_price', 'Item_total', 'total_order_price'
        ]
        results.append(delimiter.join(headers))

    for line in lines:
        # Skip header if present
        if line.lower().startswith('order_id') and 'producto' not in line.lower():
            continue
        unrolled = process_single_line(line, adjust_utc=adjust_utc, delimiter=delimiter)
        results.extend(unrolled)

    return results

def main_cli():
    import argparse
    parser = argparse.ArgumentParser(description="Desanidar líneas CSV con JSON de productos a formato plano.")
    parser.add_argument('archivo', nargs='?', help="Archivo CSV opcional a procesar")
    parser.add_argument('--tsv', action='store_true', help="Separar con tabulaciones en lugar de comas")
    parser.add_argument('--header', action='store_true', help="Incluir fila de encabezados")
    parser.add_argument('--utc-to-utc3', action='store_true', help="Ajustar fecha de UTC restando 3 horas")
    args = parser.parse_args()

    delim = "\t" if args.tsv else ","

    if args.archivo:
        with open(args.archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
    elif not sys.stdin.isatty():
        contenido = sys.stdin.read()
    else:
        print("Pega las líneas con JSON aquí. Presiona Enter y escribe 'FIN' (o presiona Enter dos veces) para procesar:\n")
        lineas = []
        while True:
            try:
                linea = input()
                if linea.strip().upper() == 'FIN' or (not linea.strip() and lineas):
                    break
                if linea.strip():
                    lineas.append(linea)
            except EOFError:
                break
        contenido = "\n".join(lineas)

    if not contenido.strip():
        print("No se ingresaron líneas para procesar.")
        return

    resultados = desanidar_texto(contenido, adjust_utc=args.utc_to_utc3, delimiter=delim, include_header=args.header)
    print("\n--- RESULTADO DESANIDADO ---\n")
    for r in resultados:
        print(r)

if __name__ == "__main__":
    main_cli()
