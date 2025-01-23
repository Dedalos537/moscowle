
import React from "react";

const AboutContent = () => {
  return (
    <div>
      <div class="container-fluid page-header" style={{marginBottom: "90px"}}>
        <div class="container">
            <div class="d-flex flex-column justify-content-center" style={{minHeight: "300px"}}>
                <h3 class="display-4 text-white text-uppercase">Acerca</h3>
                <div class="d-inline-flex text-white">
                    <p class="m-0 text-uppercase"><a class="text-white" href="">Inicio</a></p>
                    <i class="fa fa-angle-double-right pt-1 px-3"></i>
                    <p class="m-0 text-uppercase">Acerca</p>
                </div>
            </div>
        </div>
    </div>
    <div>
    <iframe src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d248.34166205759357!2d-80.64536749386156!3d-5.1890914665209!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x904a1a8fdc7e630b%3A0xfb595f6d8eb99d97!2sCentro%20de%20Terapias%20Juan%20Pablo%20II!5e0!3m2!1sfr!2spe!4v1736303806967!5m2!1sfr!2spe" width="600" height="450" style={{border:"0"}} allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
    </div>
  );
};

export default AboutContent;
