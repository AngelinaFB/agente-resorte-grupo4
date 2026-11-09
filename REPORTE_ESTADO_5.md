# REPORTE_ESTADO_5 - Validacion local de la busqueda bibliografica (Etapa 3A)

Actualizacion: 8 de noviembre de 2026. Registra la instalacion local de Ollama y BGE-M3, la generacion real de embeddings y la mejora de recuperacion. La instalacion se realizo en esta computadora; no instala Ollama para otros integrantes ni incorpora modelos al repositorio.

## Resultado de instalacion y construccion

- Ollama 0.40.15 instalado en Windows y disponible en http://127.0.0.1:11434.
- Modelo bge-m3:latest descargado mediante Ollama.
- Embeddings generados para 2.531 chunks, dimension 1.024, en 449,85 segundos (7 min 30 s).
- Base local agente-resorte/data/index/bibliografia/embeddings.sqlite: 11.882.496 bytes (unos 11,3 MiB), excluida de Git.
- La verificacion posterior del indice FTS5 termino OK; se mantuvieron conteos, referencias, ausencia de duplicados e integridad.
- Ollama informo el modelo cargado con procesador 100% GPU en este equipo. El dato no demuestra compatibilidad igual en otras GPU AMD.

## Mejora de recuperacion

Las consultas naturales sobre masa y energia no producian coincidencias FTS5 porque el modo estricto requeria que todos los terminos aparecieran literalmente. En esos casos la busqueda hibrida quedaba reducida a su rama semantica.

Se agrego un respaldo acotado a la busqueda hibrida: solo cuando FTS5 estricto devuelve cero resultados, se ejecuta una consulta OR con terminos de contenido y se fusiona por RRF con la rama semantica. La busqueda FTS5 independiente conserva su modo estricto. Los resultados FTS ahora tambien devuelven needs_ocr y quality_flags de la pagina.

Validacion automatizada: 8 pruebas de test_embeddings.py y 5 de test_index.py aprobaron (13 en total). Las consultas reales recuperan candidatos textuales y semanticos. La relevancia sigue siendo mixta: energia recupera fragmentos explicitos sobre energia cinetica/potencial; masa trae paginas sobre oscilacion, masa y frecuencia, aunque algunas candidatas son indirectas. Se requiere revision humana de fragmentos y paginas antes de declarar satisfactoria la pertinencia.

Revision del usuario: el usuario considero satisfactorios los resultados mostrados para la consulta sobre energia y acepta provisionalmente que el resto esta bien, aunque no los reviso uno por uno. Registrar esta aceptacion como criterio del usuario, separada de la evidencia automatizada; no equivale a una evaluacion humana detallada de todas las consultas.

## Recursos y limites

- El equipo medido fue distinto del declarado en el prompt: aqui se detecto Ryzen 5 5600H, aproximadamente 16 GB de RAM y Radeon RX 6600M; el perfil de referencia era Ryzen 7 5700U, 24 GB y Radeon integrada.
- Durante la generacion se observaron muestras de memoria de trabajo de llama-server cercanas a 0,9 GB. No se midio de manera fiable el pico total de RAM.
- El tiempo medido no debe extrapolarse al equipo de referencia.
- El indice fuente registra 35 documentos, 1.688 paginas y 2.531 chunks; 48 paginas requieren OCR y 105 tienen marcas de calidad. No se instalo Tesseract ni se modificaron esas marcas.

## Archivos y uso por otros integrantes

- agente-resorte/setup-chatbot.ps1: preparacion local para Windows.
- agente-resorte/chatbot/README.md: guia para preparar y usar el modulo por CLI.
- agente-resorte/chatbot/index.py: busqueda FTS y exposicion de marcas de calidad.
- agente-resorte/chatbot/embeddings.py: busqueda hibrida con respaldo FTS relajado.
- agente-resorte/tests/test_embeddings.py y test_index.py: pruebas de regresion.
- INFORME_PARA_EL_GRUPO_ETAPA_3A.md y .pdf: resumen compartible.

Ollama, BGE-M3 y las bases generadas quedan fuera del repo. Cada integrante necesita su propia instalacion y checkout con los PDF fuente. No existe un servicio compartido ni integracion con Streamlit.

No se avanzo a Etapa 3B, no se usaron servicios externos y no se modificaron los archivos excluidos por el alcance original.
