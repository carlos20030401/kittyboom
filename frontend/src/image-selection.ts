export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const imageFingerprint = (file: Pick<File, 'name' | 'size' | 'lastModified'>) => `${file.name}:${file.size}:${file.lastModified}`;
export function validateImage(file: Pick<File, 'type' | 'size'>) {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return 'Solo se permiten imágenes JPG, JPEG, PNG o WebP.';
  if (file.size > MAX_IMAGE_BYTES) return 'Cada imagen debe pesar como máximo 5 MB.';
  return null;
}

