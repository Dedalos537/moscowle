/*
 * Datos del juego: paleta, catálogo de productos, secciones de la tienda, niveles y dinero.
 * Los precios se guardan en céntimos (enteros) para no arrastrar errores de coma flotante.
 */

export const PALETTE = {
  bg: 0xd3893e,
  cream: 0xffd28f,
  cyan: 0x95e7ff,
  lilac: 0xd389ff,
  teal: 0x8fc4b8,
  brown: 0x5b3415,
  white: 0xfff8ec,
};

/*
 * shape: modelo procedural (ver models.js). label: etiqueta pintada en el atlas (texto, fondo, tinta).
 * countable: se puede pedir más de una unidad en la lista (p. ej. «3 manzanas»).
 */
export const PRODUCTS = [
  // Frutas y verduras
  { id: 'manzana', name: 'Manzana', plural: 'Manzanas', cat: 'manzana', price: 50, sec: 'frutas', shape: 'apple', countable: true },
  { id: 'platano', name: 'Plátano', plural: 'Plátanos', cat: 'platano', price: 50, sec: 'frutas', shape: 'banana', countable: true },
  { id: 'mango', name: 'Mango', plural: 'Mangos', cat: 'mango', price: 100, sec: 'frutas', shape: 'mango', countable: true },
  { id: 'limon', name: 'Limón', plural: 'Limones', cat: 'limon', price: 20, sec: 'frutas', shape: 'lime', countable: true },
  { id: 'palta', name: 'Palta', plural: 'Paltas', cat: 'palta', price: 200, sec: 'frutas', shape: 'avocado', countable: true },
  { id: 'choclo', name: 'Choclo', plural: 'Choclos', cat: 'choclo', price: 100, sec: 'frutas', shape: 'corn', countable: true },
  // Panadería
  { id: 'pan', name: 'Pan', plural: 'Panes', cat: 'pan', price: 20, sec: 'panaderia', shape: 'bun', countable: true },
  { id: 'paneton', name: 'Panetón', plural: 'Panetones', cat: 'paneton', price: 1000, sec: 'panaderia', shape: 'panettone', label: ['PANETÓN', '#2f6fd6', '#fff6d8'] },
  { id: 'galletas_choco', name: 'Galletas de chocolate', plural: 'Galletas de chocolate', cat: 'galletas', price: 250, sec: 'panaderia', shape: 'cookies', label: ['GALLETAS', '#6b3a1f', '#ffe1a8'], variant: 'de chocolate' },
  { id: 'galletas_vaini', name: 'Galletas de vainilla', plural: 'Galletas de vainilla', cat: 'galletas', price: 150, sec: 'panaderia', shape: 'cookies', label: ['GALLETAS', '#f2c94c', '#5b3415'], variant: 'de vainilla' },
  { id: 'queque', name: 'Queque', plural: 'Queques', cat: 'queque', price: 500, sec: 'panaderia', shape: 'cake' },
  // Lácteos
  { id: 'leche', name: 'Leche', plural: 'Leches', cat: 'leche', price: 400, sec: 'lacteos', shape: 'carton', label: ['LECHE', '#3c7be0', '#ffffff'], tint: 0xf4f8ff },
  { id: 'yogur', name: 'Yogur', plural: 'Yogures', cat: 'yogur', price: 300, sec: 'lacteos', shape: 'yogurt', label: ['YOGUR', '#ff7aa8', '#ffffff'], countable: true },
  { id: 'queso', name: 'Queso', plural: 'Quesos', cat: 'queso', price: 800, sec: 'lacteos', shape: 'cheese' },
  { id: 'huevos', name: 'Huevos', plural: 'Cajas de huevos', cat: 'huevos', price: 600, sec: 'lacteos', shape: 'eggs' },
  { id: 'mantequilla', name: 'Mantequilla', plural: 'Mantequillas', cat: 'mantequilla', price: 500, sec: 'lacteos', shape: 'butter', label: ['MANTEQUILLA', '#f6d55c', '#7a4b12'] },
  // Bebidas
  { id: 'agua_grande', name: 'Agua grande', plural: 'Aguas grandes', cat: 'agua', price: 300, sec: 'bebidas', shape: 'bottle_big', label: ['AGUA', '#4fb7ff', '#ffffff'], variant: 'grande', tint: 0xbfe8ff },
  { id: 'agua_chica', name: 'Agua chica', plural: 'Aguas chicas', cat: 'agua', price: 150, sec: 'bebidas', shape: 'bottle_small', label: ['AGUA', '#4fb7ff', '#ffffff'], variant: 'chica', tint: 0xbfe8ff },
  { id: 'jugo_naranja', name: 'Jugo de naranja', plural: 'Jugos de naranja', cat: 'jugo', price: 550, sec: 'bebidas', shape: 'carton', label: ['JUGO', '#ff9a2e', '#ffffff'], variant: 'de naranja', tint: 0xffe2b8 },
  { id: 'jugo_durazno', name: 'Jugo de durazno', plural: 'Jugos de durazno', cat: 'jugo', price: 350, sec: 'bebidas', shape: 'carton', label: ['JUGO', '#f7b267', '#6b3a1f'], variant: 'de durazno', tint: 0xfff0d6 },
  { id: 'gaseosa', name: 'Gaseosa', plural: 'Gaseosas', cat: 'gaseosa', price: 400, sec: 'bebidas', shape: 'soda', label: ['GASEOSA', '#2bb673', '#fff27a'], countable: true, tint: 0xffd23f },
  { id: 'chicha', name: 'Chicha morada', plural: 'Chichas moradas', cat: 'chicha', price: 450, sec: 'bebidas', shape: 'soda', label: ['CHICHA', '#7b3fa0', '#ffe3ff'], tint: 0x6a2a8c },
  // Abarrotes
  { id: 'arroz', name: 'Arroz', plural: 'Bolsas de arroz', cat: 'arroz', price: 400, sec: 'abarrotes', shape: 'sack', label: ['ARROZ', '#3aa65a', '#ffffff'] },
  { id: 'fideos', name: 'Fideos', plural: 'Paquetes de fideos', cat: 'fideos', price: 250, sec: 'abarrotes', shape: 'pasta', label: ['FIDEOS', '#e63946', '#ffe066'] },
  { id: 'aceite', name: 'Aceite', plural: 'Aceites', cat: 'aceite', price: 900, sec: 'abarrotes', shape: 'oil', label: ['ACEITE', '#f4a300', '#ffffff'], tint: 0xffc93c },
  { id: 'azucar', name: 'Azúcar', plural: 'Bolsas de azúcar', cat: 'azucar', price: 350, sec: 'abarrotes', shape: 'sack', label: ['AZÚCAR', '#ff8fab', '#ffffff'] },
  { id: 'atun', name: 'Atún', plural: 'Atunes', cat: 'atun', price: 550, sec: 'abarrotes', shape: 'can', label: ['ATÚN', '#1d6fb8', '#ffffff'], countable: true },
  { id: 'cereal_grande', name: 'Cereal grande', plural: 'Cereales grandes', cat: 'cereal', price: 1200, sec: 'abarrotes', shape: 'cereal_big', label: ['CEREAL', '#e85d3a', '#fff3b0'], variant: 'grande' },
  { id: 'cereal_chico', name: 'Cereal chico', plural: 'Cereales chicos', cat: 'cereal', price: 700, sec: 'abarrotes', shape: 'cereal_small', label: ['CEREAL', '#f7a531', '#ffffff'], variant: 'chico' },
  // Limpieza
  { id: 'jabon', name: 'Jabón', plural: 'Jabones', cat: 'jabon', price: 250, sec: 'limpieza', shape: 'soap', label: ['JABÓN', '#ff9ecf', '#ffffff'], countable: true },
  { id: 'detergente', name: 'Detergente', plural: 'Detergentes', cat: 'detergente', price: 1000, sec: 'limpieza', shape: 'jug', label: ['LIMPIO', '#2a9df4', '#ffffff'] },
  { id: 'papel', name: 'Papel higiénico', plural: 'Paquetes de papel', cat: 'papel', price: 800, sec: 'limpieza', shape: 'rolls', label: ['SUAVE', '#8ecae6', '#1d3557'] },
  { id: 'esponja', name: 'Esponja', plural: 'Esponjas', cat: 'esponja', price: 150, sec: 'limpieza', shape: 'sponge', countable: true },
  // Desayuno
  { id: 'cafe', name: 'Café', plural: 'Cafés', cat: 'cafe', price: 900, sec: 'desayuno', shape: 'jar', label: ['CAFÉ', '#5b3415', '#ffd28f'], tint: 0x4a2a14 },
  { id: 'mermelada', name: 'Mermelada', plural: 'Mermeladas', cat: 'mermelada', price: 500, sec: 'desayuno', shape: 'jam', label: ['FRESA', '#ffffff', '#d62839'], tint: 0xc81d3a },
  { id: 'avena', name: 'Avena', plural: 'Avenas', cat: 'avena', price: 400, sec: 'desayuno', shape: 'oats', label: ['AVENA', '#c08a4b', '#fff6e0'] },
  { id: 'chocolate', name: 'Chocolate', plural: 'Chocolates', cat: 'chocolate', price: 200, sec: 'desayuno', shape: 'bar', label: ['CHOCO', '#7a3e1d', '#ffd28f'], countable: true },
  { id: 'chifles', name: 'Chifles', plural: 'Bolsas de chifles', cat: 'chifles', price: 250, sec: 'desayuno', shape: 'chips', label: ['CHIFLES', '#4caf50', '#fff27a'], countable: true },
];

export const PRODUCT_BY_ID = Object.fromEntries(PRODUCTS.map((p) => [p.id, p]));

/** Nombre a mostrar en la lista para una categoría (las que tienen variantes usan un nombre genérico). */
export const CAT_NAMES = {
  galletas: ['Galletas', 'Galletas'],
  agua: ['Agua', 'Aguas'],
  jugo: ['Jugo', 'Jugos'],
  cereal: ['Cereal', 'Cereales'],
};

export function catName(cat, qty) {
  if (CAT_NAMES[cat]) return qty > 1 ? CAT_NAMES[cat][1] : CAT_NAMES[cat][0];
  const p = PRODUCTS.find((x) => x.cat === cat);
  return qty > 1 ? p.plural : p.name;
}

export function productsOfCat(cat) {
  return PRODUCTS.filter((p) => p.cat === cat);
}

/*
 * Secciones: cada una es una fila de columnas (una columna = un tipo de producto).
 * kind: 'gondola' (estante bajo), 'fridge' (refrigerador contra la pared), 'stand' (cajones de fruta).
 * x0: borde izquierdo de la primera columna; z: frente del mueble (mira hacia +z, hacia la cámara).
 */
export const SECTIONS = [
  { id: 'frutas', title: 'FRUTAS', color: 0x7cc36b, ink: '#2f6b22', kind: 'stand', x0: -10.2, z: 3.9, items: ['manzana', 'platano', 'mango', 'limon', 'palta', 'choclo'] },
  { id: 'panaderia', title: 'PANADERÍA', color: 0xe9a65a, ink: '#7a4310', kind: 'gondola', x0: -9.6, z: -0.4, items: ['pan', 'queque', 'galletas_choco', 'galletas_vaini', 'paneton'] },
  { id: 'desayuno', title: 'DESAYUNO', color: 0xff9fb2, ink: '#8a2443', kind: 'gondola', x0: 1.2, z: -0.4, items: ['chocolate', 'mermelada', 'cafe', 'avena', 'chifles'] },
  { id: 'abarrotes', title: 'ABARROTES', color: 0xf5c84b, ink: '#7a5a00', kind: 'gondola', x0: -10.1, z: -5.0, items: ['arroz', 'azucar', 'fideos', 'aceite', 'atun', 'cereal_grande', 'cereal_chico'] },
  { id: 'limpieza', title: 'LIMPIEZA', color: 0xc58cff, ink: '#5a2a8c', kind: 'gondola', x0: 1.2, z: -5.0, items: ['jabon', 'esponja', 'detergente', 'papel'] },
  { id: 'lacteos', title: 'LÁCTEOS', color: 0x95e7ff, ink: '#1d5f7a', kind: 'fridge', x0: -10.1, z: -9.3, items: ['leche', 'yogur', 'queso', 'mantequilla', 'huevos'] },
  { id: 'bebidas', title: 'BEBIDAS', color: 0x6fb6ff, ink: '#1d4f8a', kind: 'fridge', x0: 1.2, z: -9.3, items: ['agua_grande', 'agua_chica', 'gaseosa', 'chicha', 'jugo_naranja', 'jugo_durazno'] },
];

export const COLUMN_W = 1.0;

/** Límites del piso de la tienda (metros). La cámara mira desde +z (sur). */
export const STORE = { x0: -12.6, x1: 11.2, z0: -10.4, z1: 8.6 };

/** Punto de llegada a la caja: el carrito se estaciona aquí. */
export const CHECKOUT = { padX: 3.3, padZ: 3.6, padR: 1.35, counterX: 4.7, z0: 1.9, z1: 6.4 };

export const START = { x: -2.8, z: 6.5, heading: Math.PI };

/*
 * Niveles. pay: 'exact' (monedas justas), 'auto' (vuelto automático), 'change' (preguntar el vuelto).
 * memory: segundos que la lista queda a la vista. budget: hay presupuesto y variantes de precio.
 */
export const LEVELS = [
  {
    n: 1, name: 'Primera compra', goal: 'Busca 3 cosas y llévalas a la caja.',
    items: 3, maxQty: 1, sections: ['frutas', 'panaderia', 'desayuno'], intOnly: true,
    pay: 'exact', memory: 0, budget: false, npcs: 0, time: 150,
  },
  {
    n: 2, name: 'La lonchera', goal: 'Ahora algunas cosas van de a dos. ¡Mira bien los números!',
    items: 4, maxQty: 2, sections: ['frutas', 'panaderia', 'desayuno', 'lacteos'],
    pay: 'auto', memory: 0, budget: false, npcs: 1, time: 170,
  },
  {
    n: 3, name: 'Lista secreta', goal: 'Memoriza la lista: se esconderá en unos segundos.',
    items: 5, maxQty: 2, sections: ['frutas', 'panaderia', 'desayuno', 'lacteos', 'bebidas', 'abarrotes'],
    pay: 'change', memory: 14, budget: false, npcs: 1, time: 200,
  },
  {
    n: 4, name: 'Con presupuesto', goal: 'Tienes dinero contado. Elige lo que alcance.',
    items: 5, maxQty: 2, sections: ['panaderia', 'bebidas', 'abarrotes', 'lacteos', 'limpieza', 'frutas'],
    pay: 'change', memory: 0, budget: true, npcs: 1, time: 220,
  },
  {
    n: 5, name: 'Hora punta', goal: 'La tienda está llena. Recuerda tu lista y esquiva a los clientes.',
    items: 6, maxQty: 3, sections: ['frutas', 'panaderia', 'desayuno', 'lacteos', 'bebidas', 'abarrotes', 'limpieza'],
    pay: 'change', memory: 12, budget: false, npcs: 2, time: 240,
  },
  {
    n: 6, name: 'La gran compra', goal: 'Lista larga, presupuesto y memoria. ¡Tú puedes!',
    items: 8, maxQty: 2, sections: ['frutas', 'panaderia', 'desayuno', 'lacteos', 'bebidas', 'abarrotes', 'limpieza'],
    pay: 'change', memory: 18, budget: true, npcs: 2, time: 300,
  },
];

/** Monedas y billetes del Perú, en céntimos. */
export const MONEY = [
  { v: 10, kind: 'coin', label: '10', unit: 'cént.', metal: 'brass', size: 52 },
  { v: 20, kind: 'coin', label: '20', unit: 'cént.', metal: 'brass', size: 56 },
  { v: 50, kind: 'coin', label: '50', unit: 'cént.', metal: 'brass', size: 60 },
  { v: 100, kind: 'coin', label: 'S/1', unit: '', metal: 'silver', size: 64 },
  { v: 200, kind: 'coin', label: 'S/2', unit: '', metal: 'bi-gold', size: 60 },
  { v: 500, kind: 'coin', label: 'S/5', unit: '', metal: 'bi-silver', size: 68 },
  { v: 1000, kind: 'bill', label: 'S/10', unit: 'diez soles', color: 'green' },
  { v: 2000, kind: 'bill', label: 'S/20', unit: 'veinte soles', color: 'orange' },
];

export function soles(cents) {
  const s = (Math.round(cents) / 100).toFixed(2);
  return 'S/ ' + s;
}

export const MAX_CART = 14;
export const REACH = 1.55;
