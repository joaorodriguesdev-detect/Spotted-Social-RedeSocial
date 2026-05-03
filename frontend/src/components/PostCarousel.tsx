import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function PostCarousel({ images }: { images: string[] }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!images || images.length === 0) return null;

  const next = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev + 1) % images.length);
  };
  
  const prev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-zinc-800">
      {/* O 'Trilho' das imagens */}
      <div 
        className="flex transition-transform duration-300 ease-out"
        style={{ transform: `translateX(-${currentIndex * 100}%)` }}
      >
        {images.map((src, i) => (
          <div key={i} className="min-w-full flex-shrink-0">
            <img 
              src={src.startsWith('http') || src.startsWith('/') ? src : `/static/uploads/${src}`} 
              alt={`Foto do Post ${i + 1}`} 
              className="w-full h-auto max-h-[500px] object-cover" 
            />
          </div>
        ))}
      </div>

      {/* Navegação e Indicadores - Apenas se houver mais de 1 foto */}
      {images.length > 1 && (
        <>
          <button 
            onClick={prev} 
            className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/80 transition-colors z-10"
          >
            <ChevronLeft size={20} />
          </button>
          
          <button 
            onClick={next} 
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 p-1.5 rounded-full text-white hover:bg-black/80 transition-colors z-10"
          >
            <ChevronRight size={20} />
          </button>

          {/* Indicador de página tipo "dots" */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 z-10 bg-black/30 px-2 py-1 rounded-full">
            {images.map((_, i) => (
              <div 
                key={i} 
                className={`h-1.5 w-1.5 rounded-full transition-colors ${i === currentIndex ? 'bg-white' : 'bg-white/40'}`} 
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
