import { useState } from 'react';
import { Gamepad2, Play, Upload, Star, CheckCircle, Clock, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

const games = [
  {
    id: 1,
    title: 'Memoria de Colores',
    category: 'Cognitivo',
    description: 'Juego de memoria visual para mejorar concentración',
    status: 'approved',
    plays: 145,
    rating: 4.8,
    avgTime: '8 min',
    effectiveness: 92,
    thumbnail: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=400&h=300&fit=crop'
  },
  {
    id: 2,
    title: 'Palabras Mágicas',
    category: 'Lenguaje',
    description: 'Ejercicios interactivos de vocabulario y pronunciación',
    status: 'approved',
    plays: 98,
    rating: 4.6,
    avgTime: '12 min',
    effectiveness: 88,
    thumbnail: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop'
  },
  {
    id: 3,
    title: 'Laberinto Espacial',
    category: 'Motricidad',
    description: 'Coordinación visomotora mediante navegación',
    status: 'testing',
    plays: 34,
    rating: 4.2,
    avgTime: '10 min',
    effectiveness: 78,
    thumbnail: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400&h=300&fit=crop'
  },
  {
    id: 4,
    title: 'Emociones en Acción',
    category: 'Social-Emocional',
    description: 'Reconocimiento y gestión de emociones',
    status: 'pending',
    plays: 12,
    rating: 4.9,
    avgTime: '15 min',
    effectiveness: 85,
    thumbnail: 'https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?w=400&h=300&fit=crop'
  },
];

const categoryColors = {
  'Cognitivo': '#4CAF50',
  'Lenguaje': '#8BC34A',
  'Motricidad': '#2E7D32',
  'Social-Emocional': '#A5D6A7',
};

const statusConfig = {
  approved: { label: 'Aprobado', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
  testing: { label: 'En Prueba', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Clock },
  pending: { label: 'Pendiente', color: 'bg-gray-100 text-gray-700 border-gray-200', icon: Clock },
};

export function GamesModule() {
  const [selectedGame, setSelectedGame] = useState(games[0]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Módulo de Juegos Educativos</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Gestiona, prueba e integra juegos terapéuticos interactivos
          </p>
        </div>
        <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
          <Upload className="w-4 h-4 mr-2" />
          Subir Nuevo Juego
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Juegos Activos</p>
              <Gamepad2 className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">12</h3>
            <p className="text-xs text-green-600">+3 este mes</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Sesiones Jugadas</p>
              <Play className="w-5 h-5 text-blue-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">289</h3>
            <p className="text-xs text-gray-500">Este mes</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Calificación Promedio</p>
              <Star className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">4.6</h3>
            <div className="flex gap-0.5 mt-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star key={star} className="w-3 h-3 fill-yellow-500 text-yellow-500" />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Efectividad</p>
              <TrendingUp className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">86%</h3>
            <Progress value={86} className="h-2 mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Games List */}
        <Card className="lg:col-span-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Biblioteca de Juegos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {games.map((game) => {
                const status = statusConfig[game.status as keyof typeof statusConfig];
                const StatusIcon = status.icon;
                const categoryColor = categoryColors[game.category as keyof typeof categoryColors];

                return (
                  <div
                    key={game.id}
                    onClick={() => setSelectedGame(game)}
                    className={`cursor-pointer rounded-lg border transition-all hover:shadow-lg ${
                      selectedGame.id === game.id
                        ? 'border-[#4CAF50] ring-2 ring-[#4CAF50]/20'
                        : 'border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    {/* Thumbnail */}
                    <div 
                      className="h-40 rounded-t-lg bg-cover bg-center relative"
                      style={{ backgroundImage: `url(${game.thumbnail})` }}
                    >
                      <div className="absolute top-2 right-2 flex gap-2">
                        <Badge className={status.color}>
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {status.label}
                        </Badge>
                      </div>
                      <div className="absolute bottom-2 left-2">
                        <Badge 
                          style={{ 
                            backgroundColor: categoryColor,
                            color: 'white'
                          }}
                        >
                          {game.category}
                        </Badge>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="p-4">
                      <h4 className="text-sm text-gray-900 dark:text-white mb-1">{game.title}</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                        {game.description}
                      </p>
                      
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <Star className="w-3 h-3 fill-yellow-500 text-yellow-500" />
                          <span>{game.rating}</span>
                        </div>
                        <span>{game.plays} partidas</span>
                        <span>{game.avgTime}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Game Preview */}
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Vista Previa</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedGame && (
              <div className="space-y-4">
                {/* Preview Image */}
                <div 
                  className="h-48 rounded-lg bg-cover bg-center relative"
                  style={{ backgroundImage: `url(${selectedGame.thumbnail})` }}
                >
                  <div className="absolute inset-0 bg-black/40 rounded-lg flex items-center justify-center">
                    <Button className="bg-white/90 hover:bg-white text-gray-900">
                      <Play className="w-5 h-5 mr-2" />
                      Probar Juego
                    </Button>
                  </div>
                </div>

                {/* Game Info */}
                <div>
                  <h3 className="text-gray-900 dark:text-white mb-2">{selectedGame.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    {selectedGame.description}
                  </p>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Categoría</span>
                      <Badge style={{ backgroundColor: categoryColors[selectedGame.category as keyof typeof categoryColors] }}>
                        {selectedGame.category}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Estado</span>
                      <Badge className={statusConfig[selectedGame.status as keyof typeof statusConfig].color}>
                        {statusConfig[selectedGame.status as keyof typeof statusConfig].label}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Calificación</span>
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 fill-yellow-500 text-yellow-500" />
                        <span className="text-sm text-gray-900 dark:text-white">{selectedGame.rating}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Partidas</span>
                      <span className="text-sm text-gray-900 dark:text-white">{selectedGame.plays}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Tiempo Promedio</span>
                      <span className="text-sm text-gray-900 dark:text-white">{selectedGame.avgTime}</span>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Efectividad</span>
                        <span className="text-sm text-gray-900 dark:text-white">{selectedGame.effectiveness}%</span>
                      </div>
                      <Progress value={selectedGame.effectiveness} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Button className="w-full bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
                    <Play className="w-4 h-4 mr-2" />
                    Iniciar Sesión de Juego
                  </Button>
                  <Button variant="outline" className="w-full">
                    Ver Estadísticas Detalladas
                  </Button>
                  {selectedGame.status === 'testing' && (
                    <Button variant="outline" className="w-full border-[#4CAF50] text-[#4CAF50]">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Aprobar para LMS
                    </Button>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Usage Statistics */}
      <Card className="border-gray-200 dark:border-gray-800 bg-gradient-to-br from-[#E8F5E9] to-white dark:from-[#2E7D32]/10 dark:to-[#1E1E2E]">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-white">Estadísticas de Uso</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Juego Más Popular</p>
              <h4 className="text-sm text-gray-900 dark:text-white">Memoria de Colores</h4>
              <p className="text-xs text-gray-500 mt-1">145 partidas</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Mejor Calificado</p>
              <h4 className="text-sm text-gray-900 dark:text-white">Emociones en Acción</h4>
              <p className="text-xs text-gray-500 mt-1">4.9 estrellas</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Más Efectivo</p>
              <h4 className="text-sm text-gray-900 dark:text-white">Memoria de Colores</h4>
              <p className="text-xs text-gray-500 mt-1">92% efectividad</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Categoría Favorita</p>
              <h4 className="text-sm text-gray-900 dark:text-white">Cognitivo</h4>
              <p className="text-xs text-gray-500 mt-1">45% del uso total</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
