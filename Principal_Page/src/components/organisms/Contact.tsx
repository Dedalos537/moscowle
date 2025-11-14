import { useState } from "react";
import { motion } from "motion/react";
import { Mail, Phone, MapPin, Clock, Send, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Alert, AlertDescription } from "../ui/alert";

interface ContactFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  subject: string;
  message: string;
  service_interest: string;
  urgency: 'low' | 'medium' | 'high';
}

export function Contact() {
  // Estado del formulario
  const [formData, setFormData] = useState<ContactFormData>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    subject: '',
    message: '',
    service_interest: '',
    urgency: 'medium'
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [submitMessage, setSubmitMessage] = useState('');

  // Opciones de servicios
  const serviceOptions = [
    'Terapia de Lenguaje',
    'Terapia Ocupacional',
    'Terapia Física',
    'Terapia Psicológica',
    'Terapia Conductual',
    'Lecto-Escritura',
    'Apoyo Virtual',
    'Material Concreto',
    'Evaluación Inicial',
    'Consulta General'
  ];

  // Manejar cambios en los inputs
  const handleInputChange = (field: keyof ContactFormData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData(prev => ({
      ...prev,
      [field]: e.target.value
    }));
  };

  // Manejar cambios en selects
  const handleSelectChange = (field: keyof ContactFormData) => (value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Validar formulario
  const validateForm = (): string | null => {
    if (!formData.first_name.trim()) return 'El nombre es requerido';
    if (!formData.last_name.trim()) return 'El apellido es requerido';
    if (!formData.email.trim()) return 'El correo electrónico es requerido';
    if (!formData.message.trim()) return 'El mensaje es requerido';
    
    // Validar email básico
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) return 'Formato de correo electrónico inválido';
    
    if (formData.message.length < 10) return 'El mensaje debe tener al menos 10 caracteres';
    
    return null;
  };

  // Enviar formulario
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validar formulario
    const validationError = validateForm();
    if (validationError) {
      setSubmitStatus('error');
      setSubmitMessage(validationError);
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const response = await fetch('/api/public/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      // Intentar parsear JSON si viene
      let result: any = null;
      try { result = await response.json(); } catch (e) { result = null; }

      if (response.ok) {
        setSubmitStatus('success');
        setSubmitMessage((result && (result.message || result.detail)) || '¡Mensaje enviado exitosamente!');

        // Limpiar formulario
        setFormData({
          first_name: '',
          last_name: '',
          email: '',
          phone: '',
          subject: '',
          message: '',
          service_interest: '',
          urgency: 'medium'
        });
      } else {
        const errMsg = (result && (result.detail || result.message)) || `Error ${response.status}`;
        throw new Error(errMsg);
      }
    } catch (error) {
      setSubmitStatus('error');
      setSubmitMessage(error instanceof Error ? error.message : 'Error de conexión. Por favor, intenta de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };
  const contactInfo = [
    {
      icon: Phone,
      title: "Teléfono",
      content: "+51 921 507 470",
      description: "Lun - Vie, 8:00 AM - 01:00 PM /\n 3:00 PM - 7:00 PM",
    },
    {
      icon: Mail,
      title: "Correo Electrónico",
      content: "info@terapiasjuanpabloii.com",
      description: "Te respondemos en 24 horas",
    },
    {
      icon: MapPin,
      title: "Ubicación",
      content: "Jr.Vicús 311 ",
      description: "Piura, Piura",
    },
    {
      icon: Clock,
      title: "Horario",
      content: "Lun - Vie: 8:00 AM - 7:00 PM \n(Cita previa)",
      description: "Sáb: 8:00 AM - 6:00 PM (Cita previa)",
    },
  ];

  return (
    <section id="contacto" className="py-20 relative overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5" />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center justify-center p-3 rounded-2xl bg-primary/10 mb-6"
          >
            <Send className="w-8 h-8 text-primary" />
          </motion.div>
          
          <h2 className="text-3xl md:text-4xl text-foreground mb-4">
            Contáctanos
          </h2>
          
          <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Estamos aquí para ayudarte. Escríbenos y con gusto resolveremos tus dudas o agendaremos una cita.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Contact Information */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="space-y-6"
          >
            <div className="grid sm:grid-cols-2 gap-6">
              {contactInfo.map((info, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  whileHover={{ y: -4 }}
                  className="p-6 rounded-2xl bg-card/80 backdrop-blur-sm border border-border/50 shadow-lg hover:shadow-xl hover:border-primary/50 transition-all duration-300"
                >
                  <div className="p-2.5 rounded-xl bg-primary/10 text-primary w-fit mb-4">
                    <info.icon className="w-5 h-5" />
                  </div>
                  
                  <h3 className="text-foreground mb-2">
                    {info.title}
                  </h3>
                  
                  <p className="text-sm text-foreground/90 mb-1" style={{ whiteSpace: "pre-line" }}>
                    {info.content}
                  </p>
                  
                  <p className="text-xs text-muted-foreground" style={{ whiteSpace: "pre-line" }}>
                    {info.description}
                  </p>
                </motion.div>
              ))}
            </div>

            {/* Google Maps */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="h-64 rounded-2xl overflow-hidden border border-primary/20 shadow-lg"
            >
              <iframe
                src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d248.34166205759357!2d-80.64536749386156!3d-5.1890914665209!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x904a1a8fdc7e630b%3A0xfb595f6d8eb99d97!2sCentro%20de%20Terapias%20Juan%20Pablo%20II!5e0!3m2!1sfr!2spe!4v1736303806967!5m2!1sfr!2spe"
                width="100%"
                height="100%"
                style={{ border: 0 }}
                allowFullScreen={true}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                title="Centro de Terapias Juan Pablo II"
              />
            </motion.div>
          </motion.div>

          {/* Contact Form */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <div className="p-8 rounded-2xl bg-card/80 backdrop-blur-sm border border-border/50 shadow-xl">
              <h3 className="text-2xl text-foreground mb-6">
                Envíanos un mensaje
              </h3>
              
              {/* Estado del envío */}
              {submitStatus !== 'idle' && (
                <Alert className={`mb-6 ${submitStatus === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                  {submitStatus === 'success' ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600" />
                  )}
                  <AlertDescription className={submitStatus === 'success' ? 'text-green-800' : 'text-red-800'}>
                    {submitMessage}
                  </AlertDescription>
                </Alert>
              )}
              
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                    <label className="block text-sm text-foreground mb-2">
                      Nombre *
                    </label>
                    <Input 
                      value={formData.first_name}
                      onChange={handleInputChange('first_name')}
                      placeholder="Tu nombre" 
                      className="bg-background/50 border-border/50 focus:border-primary transition-colors"
                      required
                    />
                  </div>
                  
                  <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                    <label className="block text-sm text-foreground mb-2">
                      Apellido *
                    </label>
                    <Input 
                      value={formData.last_name}
                      onChange={handleInputChange('last_name')}
                      placeholder="Tu apellido" 
                      className="bg-background/50 border-border/50 focus:border-primary transition-colors"
                      required
                    />
                  </div>
                </div>
                
                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Correo Electrónico *
                  </label>
                  <Input 
                    type="email" 
                    value={formData.email}
                    onChange={handleInputChange('email')}
                    placeholder="tu@email.com" 
                    className="bg-background/50 border-border/50 focus:border-primary transition-colors"
                    required
                  />
                </div>
                
                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Teléfono
                  </label>
                  <Input 
                    type="tel" 
                    value={formData.phone}
                    onChange={handleInputChange('phone')}
                    placeholder="+51 900-000-000" 
                    className="bg-background/50 border-border/50 focus:border-primary transition-colors"
                  />
                </div>

                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Asunto
                  </label>
                  <Input 
                    value={formData.subject}
                    onChange={handleInputChange('subject')}
                    placeholder="Asunto de tu mensaje" 
                    className="bg-background/50 border-border/50 focus:border-primary transition-colors"
                  />
                </div>

                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Servicio de Interés
                  </label>
                  <Select value={formData.service_interest} onValueChange={handleSelectChange('service_interest')}>
                    <SelectTrigger className="bg-white/95 dark:bg-slate-900 border-border/50 focus:border-primary transition-colors" style={{ backgroundColor: 'var(--popover)', zIndex: 9999 }}>
                      <SelectValue placeholder="Selecciona un servicio (opcional)" />
                    </SelectTrigger>
                    <SelectContent align="end" sideOffset={6} className="bg-white dark:bg-slate-900 origin-top-right data-[side=bottom]:translate-y-2 rounded-tr-xl rounded-tl-xl rounded-bl-2xl shadow-lg" style={{ backgroundColor: 'var(--popover)', zIndex: 9999 }}>
                      {serviceOptions.map((service) => (
                        <SelectItem key={service} value={service}>
                          {service}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Prioridad
                  </label>
                  <Select value={formData.urgency} onValueChange={handleSelectChange('urgency')}>
                    <SelectTrigger className="bg-white/95 dark:bg-slate-900 border-border/50 focus:border-primary transition-colors" style={{ backgroundColor: 'var(--popover)', zIndex: 9999 }}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent align="end" sideOffset={6} className="bg-white dark:bg-slate-900 origin-top-right data-[side=bottom]:translate-y-2 rounded-tr-xl rounded-tl-xl rounded-bl-2xl shadow-lg" style={{ backgroundColor: 'var(--popover)', zIndex: 9999 }}>
                      <SelectItem value="low">Baja - Consulta general</SelectItem>
                      <SelectItem value="medium">Media - Información sobre servicios</SelectItem>
                      <SelectItem value="high">Alta - Necesito agendar una cita pronto</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="transition-transform duration-200 focus-within:-translate-y-0.5 focus-within:shadow-md focus-within:ring-1 focus-within:ring-primary/20 rounded-lg">
                  <label className="block text-sm text-foreground mb-2">
                    Mensaje *
                  </label>
                  <Textarea 
                    value={formData.message}
                    onChange={handleInputChange('message')}
                    placeholder="¿Cómo podemos ayudarte? Describe tu consulta o situación..." 
                    rows={5}
                    className="bg-background/50 border-border/50 focus:border-primary transition-colors resize-none"
                    required
                    minLength={10}
                  />
                  <div className="mt-2">
                    <div className="h-1 rounded-full bg-muted/20 overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${Math.min(100, Math.round((formData.message.length / 2000) * 100))}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2 flex justify-between">
                      <span>Mínimo 10 caracteres.</span>
                      <span>{formData.message.length}/2000</span>
                    </p>
                  </div>
                </div>
                
                <div>
                  <Button 
                    type="submit" 
                    disabled={isSubmitting}
                    className={`w-full bg-primary hover:bg-primary/90 text-primary-foreground group disabled:opacity-50 transition-transform ${submitStatus === 'success' ? 'ring-2 ring-green-300 scale-102' : ''}`}
                    size="lg"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 w-5 h-5 animate-spin" />
                        Enviando...
                      </>
                    ) : submitStatus === 'success' ? (
                      <div className="flex items-center justify-center gap-2">
                        <CheckCircle className="w-5 h-5 text-white animate-pulse" />
                        <span>Enviado</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-2">
                        <span>Enviar Mensaje</span>
                        <Send className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </div>
                    )}
                  </Button>
                </div>
                
                <p className="text-xs text-muted-foreground text-center">
                  Los campos marcados con * son obligatorios. 
                  Te responderemos dentro de las próximas 24 horas.
                </p>
              </form>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
