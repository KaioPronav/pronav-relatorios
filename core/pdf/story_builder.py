# core/pdf/story_builder.py
import math
from reportlab.platypus import Spacer
from .tables_builder import EquipmentTableBuilder, SectionsTableBuilder, ActivitiesTableBuilder

class StoryBuilder:
    def __init__(self, config, styles, pad_small, pad_med, usable_w, square_side, line_width, gray, font_manager, utils, format_date_br, ensure_upper_safe):
        self.config = config
        self.styles = styles
        self.pad_small = pad_small
        self.pad_med = pad_med
        self.usable_w = usable_w
        self.square_side = square_side
        self.LINE_WIDTH = line_width
        self.GRAY = gray
        self.font_manager = font_manager
        self.utils = utils
        self.format_date_br = format_date_br
        self.ensure_upper_safe = ensure_upper_safe

        # builders
        self.equip_builder = EquipmentTableBuilder(styles, gray, line_width, pad_small)
        self.sections_builder = SectionsTableBuilder(styles, gray, line_width, pad_small)
        self.activities_builder = ActivitiesTableBuilder(styles, gray, line_width, pad_small, ensure_upper_safe, format_date_br)

    def build_story(self, report_request, atividades_list, equipments_list, frame_height=None):
        """
        Constrói a story (lista de flowables) garantindo:
        - medição do espaço já ocupado na primeira página (page_top_offset)
          para passar ao SectionsTableBuilder;
        - espaçamento mínimo entre blocos para PDF compacto.
        """
        story_local = []

        # spacer inicial bem pequeno (evita deslocamentos desnecessários)
        story_local.append(Spacer(1, 1))  # 1 pt

        # equipment
        equip_table = self.equip_builder.build(report_request, equipments_list, self.usable_w)
        story_local.append(equip_table)

        # spacer mínimo entre equipamentos e seções (compacto)
        small_spacer = Spacer(1, 2)  # 2 pts
        story_local.append(small_spacer)

        # MEDIR quanto já foi usado na página (somente os elementos acima)
        used_top_h = 0.0
        # se frame_height for None, passamos um valor grande para wrap (wrap requer um max height)
        wrap_max_h = frame_height if frame_height is not None else 10000.0

        for f in story_local:
            try:
                # se o objeto tem wrap (Table, Paragraph, etc.), usamos wrap para obter altura real
                if hasattr(f, 'wrap'):
                    try:
                        _, h = f.wrap(self.usable_w, wrap_max_h)
                        used_top_h += float(h or 0.0)
                        continue
                    except Exception:
                        pass
                # se é Spacer (ou similar) usamos atributo height
                if hasattr(f, 'height'):
                    try:
                        used_top_h += float(getattr(f, 'height') or 0.0)
                        continue
                    except Exception:
                        pass
            except Exception:
                # em casos estranhos, ignora e segue
                continue

        # garantir valor inteiro para satisfazer o tipo esperado e evitar truncamento
        page_top_offset = int(math.ceil(used_top_h)) if used_top_h else 0

        # sections (reutilizamos a lista original)
        sections = [
            ("PROBLEMA RELATADO/ENCONTRADO", report_request.PROBLEMA_RELATADO),
            ("SERVIÇO REALIZADO", report_request.SERVICO_REALIZADO),
            ("RESULTADO", report_request.RESULTADO),
            ("PENDÊNCIAS", report_request.PENDENCIAS),
            ("MATERIAL FORNECIDO PELO CLIENTE", report_request.MATERIAL_CLIENTE),
            ("MATERIAL FORNECIDO PELA PRONAV", report_request.MATERIAL_PRONAV),
        ]

        # Passa page_top_offset para as seções para evitar títulos órfãos
        section_flowables = self.sections_builder.build(
            sections,
            self.usable_w,
            frame_height=frame_height,
            page_top_offset=page_top_offset
        )
        story_local.extend(section_flowables)

        # activities
        if atividades_list:
            activities_table = self.activities_builder.build(atividades_list, self.usable_w, self.square_side)
            story_local.append(activities_table)

        return story_local
