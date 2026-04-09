import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatarHoras(valor: number): string {
  // Obtém a parte inteira (horas)
  const horas = Math.floor(valor);
  
  // Obtém a parte decimal e converte para minutos (60 * decimal)
  // Arredondamos para evitar problemas de precisão do JS (ex: 0.1 + 0.2)
  const minutos = Math.round((valor - horas) * 60);

  // Retorna formatado. Se os minutos forem 0, você pode optar por exibir apenas a hora.
  if (minutos === 0) {
    return `${horas}h`;
  }

  return `${horas}h ${minutos}min`;
}