from fpdf import FPDF
from datetime import date
import io

class PDFReport(FPDF):
    def header(self):
        # Logo de la empresa (si hubiera)
        # self.image('logo.png', 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Despacho Contable - Reporte Mensual de Impuestos', ln=True, align='C')
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generado el {date.today().strftime("%d/%m/%Y")} - Página {self.page_no()}/{{nb}}', align='C')

def generar_pdf(cliente_datos, periodo, resultados_impuestos, df_facturas):
    """
    Genera un archivo PDF con el resumen de impuestos calculados.
    """
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Datos del Cliente
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'DATOS DEL CONTRIBUYENTE', ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(50, 8, f"Nombre / Razón Social: ", 0, 0)
    pdf.cell(0, 8, f"{cliente_datos['nombre']}", 0, 1)
    
    pdf.cell(50, 8, f"RFC:", 0, 0)
    pdf.cell(0, 8, f"{cliente_datos['rfc']} ({cliente_datos['tipo_persona']})", 0, 1)
    
    pdf.cell(50, 8, f"Régimen Fiscal:", 0, 0)
    pdf.cell(0, 8, f"{cliente_datos['regimen']}", 0, 1)
    
    pdf.cell(50, 8, f"Periodo Calculado:", 0, 0)
    pdf.cell(0, 8, f"{periodo}", 0, 1)
    
    pdf.ln(5)
    
    # Resumen Financiero
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'RESUMEN FINANCIERO MENSUAL (BASE FLUJO DE EFECTIVO - PUE)', ln=True, border='B')
    pdf.set_font('Arial', '', 11)
    
    pdf.cell(100, 8, 'Total de Ingresos Cobrados:', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['Ingresos_Totales']:,.2f}", 0, 1, 'R')
    
    pdf.cell(100, 8, 'Total de Gastos Pagados:', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['Gastos_Totales']:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'I', 11)
    pdf.cell(100, 8, 'Utilidad Bruta (Ingresos - Gastos):', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['Utilidad_Fiscal_Base']:,.2f}", 0, 1, 'R')
    
    pdf.ln(5)
    
    # Impuestos Determindos
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'CÁLCULO DE IMPUESTOS (ISR E IVA)', ln=True, border='B')
    pdf.set_font('Arial', '', 11)
    
    # ISR
    pdf.cell(100, 8, f"ISR Determinado (Tasa: {resultados_impuestos['Tasa_ISR_Aplicada']}):", 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['ISR_Determinado']:,.2f}", 0, 1, 'R')
    
    pdf.cell(100, 8, 'Menos ISR Retenido por Terceros:', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['ISR_Retenido']:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 11)
    if resultados_impuestos['ISR_A_Favor'] > 0:
         pdf.cell(100, 8, 'ISR A FAVOR:', 0, 0)
         pdf.cell(0, 8, f"$ {resultados_impuestos['ISR_A_Favor']:,.2f}", 0, 1, 'R')
    else:
         pdf.cell(100, 8, 'ISR A PAGAR:', 0, 0)
         pdf.set_text_color(220, 20, 60) # Rojo si hay pago
         pdf.cell(0, 8, f"$ {resultados_impuestos['ISR_A_Pagar']:,.2f}", 0, 1, 'R')
         pdf.set_text_color(0, 0, 0)
         
    pdf.ln(3)
    
    # IVA
    pdf.set_font('Arial', '', 11)
    pdf.cell(100, 8, 'IVA Trasladado (Cobrado a Clientes):', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['IVA_Cobrado']:,.2f}", 0, 1, 'R')
    
    pdf.cell(100, 8, 'Menos IVA Acreditable (Pagado en Gastos):', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['IVA_Pagado']:,.2f}", 0, 1, 'R')
    
    pdf.cell(100, 8, 'Menos IVA Retenido:', 0, 0)
    pdf.cell(0, 8, f"$ {resultados_impuestos['IVA_Retenido']:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 11)
    if resultados_impuestos['IVA_A_Favor'] > 0:
         pdf.cell(100, 8, 'IVA A FAVOR:', 0, 0)
         pdf.cell(0, 8, f"$ {resultados_impuestos['IVA_A_Favor']:,.2f}", 0, 1, 'R')
    else:
         pdf.cell(100, 8, 'IVA A PAGAR:', 0, 0)
         pdf.set_text_color(220, 20, 60) # Rojo
         pdf.cell(0, 8, f"$ {resultados_impuestos['IVA_A_Pagar']:,.2f}", 0, 1, 'R')
         pdf.set_text_color(0, 0, 0)
         
    pdf.ln(5)
    
    # Total
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(100, 12, 'TOTAL DE IMPUESTOS A PAGAR:', 0, 0, fill=True)
    pdf.set_text_color(220, 20, 60)
    pdf.cell(0, 12, f"$ {resultados_impuestos['Total_Impuestos_A_Pagar']:,.2f}", 0, 1, 'R', fill=True)
    pdf.set_text_color(0, 0, 0)
    
    pdf.ln(15)
    
    # Notas Finales
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 6, "NOTA: Este cálculo es preliminar y se basa en los archivos XML proporcionados "
                         "y procesados automáticamente. El pago deberá realizarse antes de la fecha límite establecida "
                         "en su calendario de obligaciones para evitar recargos y actualizaciones.")
                         
    # Devolver como bytes
    # FPDF output defaults to string, need to convert to bytes for Streamlit download
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return pdf_bytes
