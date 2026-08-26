export function normalizeWhatsAppNumber(value?: string | null) {
  const digits = (value ?? '').replace(/\D/g, '');
  if (!digits) return '';
  return digits.length === 9 ? `51${digits}` : digits;
}

export function buildWhatsAppUrl(number: string | null | undefined, message: string) {
  const normalized = normalizeWhatsAppNumber(number);
  if (!normalized) throw new Error('No hay un número de WhatsApp configurado.');
  return `https://wa.me/${normalized}?text=${encodeURIComponent(message)}`;
}

