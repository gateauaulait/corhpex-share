// -*- tab-width: 2; indent-tabs-mode: nil; coding: utf-8-with-signature -*-
//-----------------------------------------------------------------------------
// Copyright 2000-2022 CEA (www.cea.fr) IFPEN (www.ifpenergiesnouvelles.com)
// See the top-level COPYRIGHT file for details.
// SPDX-License-Identifier: Apache-2.0
//-----------------------------------------------------------------------------
/*
 * CapillaryPressureLaw.h
 */

//-----------------------------------------------------------
// Loi de la pression capillaire
// Pc = Pe (Sw)^(-1/lambda)
//-----------------------------------------------------------

#ifndef CAPILLARYPRESSURELAW_H_
#define CAPILLARYPRESSURELAW_H_

#include <algorithm>
#include <math.h>

#ifndef EVAL_VF
#define EVAL_NAIVE
#endif

//=====================================================

template <typename FpStore, typename FpComp> class CapillaryPressureLaw {
public:
  // Constructeur Obligatoire
  CapillaryPressureLaw() { initParameters(); }

  // Evaluation of function and derivatives
#pragma omp declare simd
  inline void eval(const FpComp S, FpStore &Pc, FpStore &dPc_dS) const {
    FpComp dSe_dS;
    const FpComp Se = computeSe(S, dSe_dS);
    FpComp alpha = (FpComp)-1 / m_lambda;
    if (Se) {
      Pc = m_Pe * pow(Se, alpha);
      dPc_dS = alpha * m_Pe * dSe_dS * pow(Se, alpha - 1);
    } else {
      Pc = 0.;     // infinity
      dPc_dS = 0.; // -infinity
    }
  }

  void setParameters(const FpComp Pe, const FpComp Sr_ref, const FpComp Sr,
                     const FpComp lambda) {
    // Set Parameters

    m_Pe = Pe;
    m_Sr_ref = Sr_ref;
    m_Sr = Sr;
    m_lambda = lambda;
  }

private:
  void initParameters() noexcept {
    // Init Parameters
    // Standard End Points
    const FpComp Pe = 0;
    const FpComp Sr_ref = 0;
    const FpComp Sr = 0;
    const FpComp lambda = 1;

    // Set Parameters
    setParameters(Pe, Sr_ref, Sr, lambda);
  }

#pragma omp declare simd
  inline FpComp computeSe(const FpComp S, FpComp &dSe_dS) const {
    FpComp Se = std::min((FpComp)1 - (S - m_Sr) / ((FpComp)1 - m_Sr_ref - m_Sr),
                         (FpComp)1);
    dSe_dS = (FpComp)-1 / ((FpComp)1 - m_Sr_ref - m_Sr);

    return std::max(Se, (FpComp)0);
  }

private:
  FpComp m_Pe;
  FpComp m_Sr_ref;
  FpComp m_Sr;
  FpComp m_lambda;
};

#endif /* CAPILLARYPRESSURELAW_H_ */
