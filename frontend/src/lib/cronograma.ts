export type CronogramaItem = { horario: string; atividade: string };
export type DiaSemana = "segunda" | "terca" | "quarta" | "quinta" | "sexta" | "sabado" | "domingo";

export const CRONOGRAMA: Record<DiaSemana, CronogramaItem[]> = {
  segunda: [
    { horario: "15:00-15:52", atividade: "Física (teoria/questões)" },
    { horario: "16:00-16:52", atividade: "Português (teoria/questões)" },
    { horario: "17:00-17:52", atividade: "Escola" },
    { horario: "18:00-18:52", atividade: "Matemática (teoria)" },
    { horario: "19:30-20:22", atividade: "História (teoria)" },
    { horario: "20:30-21:22", atividade: "Questões Matemática" },
  ],
  terca: [
    { horario: "15:00-15:52", atividade: "Química (teoria)" },
    { horario: "16:00-16:52", atividade: "Questões Química" },
    { horario: "17:00-17:52", atividade: "Inglês (teoria/questões)" },
    { horario: "18:00-18:52", atividade: "Português (teoria/questões)" },
    { horario: "19:30-20:22", atividade: "Questões Matemática" },
    { horario: "20:30-21:00", atividade: "Escola" },
  ],
  quarta: [
    { horario: "15:00-15:52", atividade: "Português (teoria)" },
    { horario: "16:00-16:52", atividade: "Questões Português" },
    { horario: "17:00-17:52", atividade: "Geografia (teoria)" },
    { horario: "18:00-18:52", atividade: "Escola" },
    { horario: "19:30-20:22", atividade: "Questões História" },
    { horario: "20:30-21:00", atividade: "Questões Geografia" },
  ],
  quinta: [{ horario: "20:00-20:52", atividade: "Questões História" }],
  sexta: [{ horario: "20:00-20:52", atividade: "Questões Matemática/Física" }],
  sabado: [
    { horario: "08:00-08:52", atividade: "Matemática pesada" },
    { horario: "09:00-09:52", atividade: "Física/Química" },
    { horario: "10:00-10:52", atividade: "Questões" },
    { horario: "14:00-18:30", atividade: "Simulado completo" },
  ],
  domingo: [
    { horario: "09:00-09:52", atividade: "Redação (teoria)" },
    { horario: "10:00-10:52", atividade: "Revisão do simulado" },
    { horario: "16:00-16:52", atividade: "Redação (prática)" },
    { horario: "17:00-17:52", atividade: "Correção do simulado" },
  ],
};

export const DIAS_ORDEM: DiaSemana[] = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"];

export const DIAS_LABEL: Record<DiaSemana, { full: string; short: string }> = {
  segunda: { full: "Segunda", short: "SEG" },
  terca: { full: "Terça", short: "TER" },
  quarta: { full: "Quarta", short: "QUA" },
  quinta: { full: "Quinta", short: "QUI" },
  sexta: { full: "Sexta", short: "SEX" },
  sabado: { full: "Sábado", short: "SÁB" },
  domingo: { full: "Domingo", short: "DOM" },
};

// JS getDay: 0=domingo .. 6=sabado
export function getDiaAtual(date = new Date()): DiaSemana {
  const map: DiaSemana[] = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"];
  return map[date.getDay()];
}

export function parseHorario(horario: string): { startMin: number; endMin: number } {
  const [start, end] = horario.split("-");
  const toMin = (s: string) => {
    const [h, m] = s.split(":").map(Number);
    return h * 60 + m;
  };
  return { startMin: toMin(start), endMin: toMin(end) };
}

export function isHorarioAtual(horario: string, date = new Date()): boolean {
  const { startMin, endMin } = parseHorario(horario);
  const nowMin = date.getHours() * 60 + date.getMinutes();
  return nowMin >= startMin && nowMin <= endMin;
}
