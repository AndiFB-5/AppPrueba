#!/usr/bin/env python3
import sys
import os
import csv
import json
from datetime import datetime, timezone, timedelta

TZ_UTC_3 = timezone(timedelta(hours=-3))

MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

def format_num(val):
    try:
        val_float = float(val)
        if val_float.is_integer():
            return int(val_float)
        return round(val_float, 2)
    except (ValueError, TypeError):
        return val

def parse_json_column(val):
    """Intenta parsear un valor como lista de productos en JSON."""
    if not isinstance(val, str):
        return None
    val_clean = val.strip()
    if not (val_clean.startswith('[') and val_clean.endswith(']')):
        return None
    
    # Manejar posibles comillas dobles escapadas de CSV ("")
    try:
        data = json.loads(val_clean)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data
    except Exception:
        pass

    try:
        # Intentar reemplazando comillas dobles dobles
        data = json.loads(val_clean.replace('""', '"'))
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data
    except Exception:
        pass

    return None

def detect_delimiter(text):
    first_line = text.splitlines()[0] if text else ""
    if '\t' in first_line:
        return '\t'
    if ';' in first_line:
        return ';'
    return ','

def process_table_rows(rows):
    """
    Recibe una lista de filas (listas de strings) y desanida la columna JSON de productos.
    """
    output_rows = []

    for row in rows:
        if not row or all(not str(c).strip() for c in row):
            continue

        # Buscar cuál columna contiene el JSON
        json_col_idx = None
        products_list = None

        for idx, col in enumerate(row):
            parsed = parse_json_column(col)
            if parsed is not None:
                json_col_idx = idx
                products_list = parsed
                break

        # Si no tiene JSON, puede ser encabezado u otra fila
        if json_col_idx is None:
            # Si contiene 'productos' o similar en el encabezado, expandirlo
            header_expanded = []
            found_header = False
            for col in row:
                if str(col).strip().lower() in ['productos', 'items']:
                    header_expanded.extend(['product_name', 'quantity', 'item_price', 'Item_total'])
                    found_header = True
                else:
                    header_expanded.append(col)
            output_rows.append(header_expanded if found_header else row)
            continue

        # Columnas previas al JSON
        prefix_cols = list(row[:json_col_idx])

        # Extraer total general (último valor numérico no vacío de la fila original)
        total_order_price = None
        for col in reversed(row[json_col_idx + 1:]):
            val_clean = str(col).strip().replace('$', '').replace(',', '')
            try:
                total_order_price = format_num(float(val_clean))
                break
            except ValueError:
                continue

        # Si no se encontró un total al final, calcularlo sumando los items
        if total_order_price is None:
            calc_total = 0.0
            for item in products_list:
                qty = float(item.get('cantidad') or item.get('quantity') or 1)
                price = float(item.get('precio_unitario') or item.get('item_price') or 0.0)
                calc_total += qty * price
            total_order_price = format_num(calc_total)

        # Generar una fila por cada ítem
        for item in products_list:
            prod_name = item.get('producto') or item.get('product_name') or ''
            qty = format_num(item.get('cantidad') or item.get('quantity') or 1)
            unit_price = format_num(item.get('precio_unitario') or item.get('item_price') or 0.0)
            
            try:
                item_total = format_num(float(qty) * float(unit_price))
            except (ValueError, TypeError):
                item_total = unit_price

            new_row = prefix_cols + [prod_name, qty, unit_price, item_total, total_order_price]
            output_rows.append(new_row)

    return output_rows

def convert_string(text, delimiter=None):
    if not text.strip():
        return ""
    if delimiter is None:
        delimiter = detect_delimiter(text)

    import io
    input_file = io.StringIO(text)
    reader = csv.reader(input_file, delimiter=delimiter)
    rows = list(reader)

    expanded_rows = process_table_rows(rows)

    output_file = io.StringIO()
    writer = csv.writer(output_file, delimiter=delimiter)
    for r in expanded_rows:
        writer.writerow(r)

    return output_file.getvalue()

def convert_file(input_path, output_path=None, delimiter=None):
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    if delimiter is None:
        delimiter = detect_delimiter(content)

    converted = convert_string(content, delimiter=delimiter)

    if output_path:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(converted)
        print(f"[OK] Archivo convertido exitosamente a: {output_path}")
    else:
        sys.stdout.write(converted)

def main_cli():
    import argparse
    parser = argparse.ArgumentParser(description="Desanidar productos JSON en registros de pedidos a filas individuales.")
    parser.add_argument("input", nargs="?", help="Ruta del archivo de entrada (.csv o .tsv). Si se omite, lee de la entrada estándar (stdin).")
    parser.add_argument("output", nargs="?", help="Ruta del archivo de salida. Si se omite, imprime en la salida estándar.")
    parser.add_argument("-d", "--delimiter", help="Delimitador (por ejemplo ',' o '\\t'). Por defecto se detecta automáticamente.")

    args = parser.parse_args()

    delim = None
    if args.delimiter:
        delim = '\t' if args.delimiter in ['\\t', 'tab'] else args.delimiter

    if args.input:
        convert_file(args.input, args.output, delimiter=delim)
    else:
        if sys.stdin.isatty():
            print("Pega el contenido con JSON a desanidar y presiona Ctrl+D (EOF):", file=sys.stderr)
        content = sys.stdin.read()
        if content:
            sys.stdout.write(convert_string(content, delimiter=delim))

if __name__ == "__main__":
    main_cli()
