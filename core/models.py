from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import List, Optional, Dict, Any

class Activity(BaseModel):
    DATA: str
    HORA: Optional[str] = None
    HORA_INICIO: Optional[str] = None
    HORA_FIM: Optional[str] = None
    TIPO: str
    KM: Optional[str] = None
    DESCRICAO: Optional[str] = ''
    TECNICO1: str
    TECNICO2: Optional[str] = None
    MOTIVO: Optional[str] = None
    ORIGEM: Optional[str] = None
    DESTINO: Optional[str] = None

    @field_validator('DATA', 'TIPO', 'TECNICO1', mode='before')
    @classmethod
    def validate_required(cls, v):
        if v is None:
            raise ValueError('Campo obrigatório não preenchido')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Campo obrigatório não preenchido')
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode='after')
    def check_hours_present_and_km(self):
        # --- validação de hora ---
        if self.HORA and isinstance(self.HORA, str) and self.HORA.strip():
            pass
        elif (self.HORA_INICIO and isinstance(self.HORA_INICIO, str) and self.HORA_INICIO.strip()
            and self.HORA_FIM and isinstance(self.HORA_FIM, str) and self.HORA_FIM.strip()):
            pass
        else:
            raise ValueError('Informe HORA (formato antigo) ou HORA_INICIO e HORA_FIM')

        # --- validação de KM ---
        tipos_sem_km = {"Mão-de-obra Técnica", "Período de Espera", "Viagem Aérea", "Translado"}
        tipo_norm = (self.TIPO or '').strip()

        if tipo_norm not in tipos_sem_km:
            if self.KM is None or (isinstance(self.KM, str) and not self.KM.strip()):
                raise ValueError('Campo KM obrigatório para este tipo de atividade')
        else:
            # Se for tipo sem KM → garante que KM sempre venha vazio
            self.KM = ""
        return self


class ReportRequest(BaseModel):
    user_id: str
    CLIENTE: str
    NAVIO: str
    CONTATO: str
    OBRA: str
    LOCAL: str
    OS: str
    EQUIPAMENTO: Optional[str] = ''
    FABRICANTE: Optional[str] = ''
    MODELO: Optional[str] = ''
    NUMERO_SERIE: Optional[str] = ''
    PROBLEMA_RELATADO: str
    SERVICO_REALIZADO: str
    RESULTADO: str
    PENDENCIAS: str
    MATERIAL_CLIENTE: str
    MATERIAL_PRONAV: str
    activities: List[Activity]
    EQUIPAMENTOS: Optional[List[Dict[str, Any]]] = None
    CIDADE: Optional[str] = None
    ESTADO: Optional[str] = None

    @field_validator('user_id', 'CLIENTE', 'NAVIO', 'CONTATO', 'OBRA', 'LOCAL', 'OS',
                     'PROBLEMA_RELATADO', 'SERVICO_REALIZADO', 'RESULTADO',
                     'PENDENCIAS', 'MATERIAL_CLIENTE', 'MATERIAL_PRONAV')
    @classmethod
    def validate_required_fields(cls, v):
        if v is None:
            raise ValueError('Campo obrigatório não preenchido')
        if isinstance(v, str) and not v.strip():
            raise ValueError('Campo obrigatório não preenchido')
        return v.strip() if isinstance(v, str) else v