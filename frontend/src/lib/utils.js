// frontend/src/lib/utils.js (necessário para os componentes Shadcn/UI)
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}