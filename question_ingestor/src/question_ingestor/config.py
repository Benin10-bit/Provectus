from dataclasses import dataclass, field, asdict
import json, hashlib

@dataclass
class Config:
    generic_filename_patterns: list = field(default_factory=lambda: [r'lista-questoes-\d+'])
    discovery_ignore_directories: list = field(default_factory=lambda: ['__MACOSX','storage','raw','staging','.venv','node_modules'])
    profile: str = 'fenix-single-column-v1'
    schema_version: int = 2
    raw_schema_version: int = 2
    inline_vertical_overlap: float = 0.45
    baseline_tolerance: float = 2.0
    horizontal_gap_em: float = 2.0
    geometry_epsilon: float = 0.75
    overlap_ratio_threshold: float = 0.10
    drawing_join_tolerance: float = 2.0
    table_max_row_gap: float = 72.0
    table_header_rows: float = 1.6
    glyph_origin_tolerance: float = 0.5
    webp_quality: int = 95
    dpi: int = 144
    lossless_webp: bool = True
    recurrence_ratio: float = .9
    min_recurrence_pages: int = 3
    margin_ratio: float = .11
    position_tolerance: float = 2
    header_min_size: float = 11.5
    header_x_tolerance: float = 3
    header_wrap_gap: float = 10
    alternative_indent: float = 7.5
    alternative_x_tolerance: float = 3
    asset_padding: float = 1.5
    inline_image_max_height: float = 35
    min_asset_area: float = 1
    min_statement_chars: int = 20
    formula_gap_pattern: str = r'\b(?:capacitância|distância|carga|resistência|tensão|área|volume|pressão|velocidade|aceleração|energia|massa|coeficiente)\s+(?:de|é|igual a)\s*\.(?!\.)'
    min_alternatives: int = 2
    max_alternatives: int = 8
    review_sample_size: int = 75
    similarity_threshold: float = .94
    save_originals: bool = True
    header_pattern: str = r'^Questão\s+(\d+)\s*[-–—]\s*(.*?)\s*[-–—]\s*Dificuldade:\s*(.*?)\s*$'
    header_start_pattern: str = r'^Questão\s+\d+\b'
    alternative_pattern: str = r'^([A-Z])\)\s*(.*)$'
    answer_pattern: str = r'^Gabarito:\s*(\S+)\s*$'
    aliases: dict = field(default_factory=lambda: {
        'Escola Preparatória de Cadetes do Exército': 'EsPCEx',
        'Instituto Tecnológico de Aeronáutica': 'ITA',
        'Instituto Militar de Engenharia': 'IME',
        'Universidade Estadual do Ceará': 'UECE',
        'Escola Naval': 'EN', 'Academia da Força Aérea': 'AFA',
        'Escola de Formação de Oficiais da Marinha Mercante': 'EFOMM',
        'Oficial de Carreira do Corpo de Bombeiros Militares': 'CBMERJ',
        'EsPCEx':'EsPCEx','EEAr':'EEAr','AFA':'AFA','EFOMM':'EFOMM',
    })
    difficulties: dict = field(default_factory=lambda: {'Fácil':'FACIL','Média':'MEDIA','Difícil':'DIFICIL','Muito Difícil':'MUITO_DIFICIL'})

    def raw_fingerprint(self):
        values={k:getattr(self,k) for k in ['raw_schema_version','recurrence_ratio','min_recurrence_pages','margin_ratio','position_tolerance','glyph_origin_tolerance']}
        values['raw_engine_revision']=5
        return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    @classmethod
    def load(cls, path=None):
        return cls(**json.loads(path.read_text())) if path else cls()
